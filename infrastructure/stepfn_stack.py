"""
AWS Step Functions Stack for VisaMate AI Visa Wizard Flow.
Creates an Express workflow for the complete visa application process.
"""

from aws_cdk import (
    Stack,
    Duration,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as tasks,
    aws_lambda as _lambda,
    aws_iam as iam,
    aws_logs as logs,
    CfnOutput
)
from constructs import Construct


class VisaMateStepFunctionStack(Stack):
    """Step Functions stack for Visa Wizard workflow."""

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create Lambda functions for the workflow
        self.lambdas = self._create_workflow_lambdas()
        
        # Create the Step Function state machine
        self.state_machine = self._create_visa_wizard_workflow()
        
        # Create outputs
        self._create_outputs()

    def _create_workflow_lambdas(self) -> dict:
        """Create Lambda functions for the workflow steps."""
        
        # Common Lambda execution role
        lambda_role = iam.Role(
            self, "WorkflowLambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole")
            ],
            inline_policies={
                "WorkflowPolicy": iam.PolicyDocument(
                    statements=[
                        # DynamoDB permissions
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "dynamodb:GetItem",
                                "dynamodb:PutItem",
                                "dynamodb:UpdateItem",
                                "dynamodb:Query"
                            ],
                            resources=[
                                f"arn:aws:dynamodb:us-east-1:790791784202:table/visamate-ai-*"
                            ]
                        ),
                        # S3 permissions
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "s3:GetObject",
                                "s3:ListBucket"
                            ],
                            resources=[
                                "arn:aws:s3:::visamate-documents",
                                "arn:aws:s3:::visamate-documents/*"
                            ]
                        )
                    ]
                )
            }
        )

        lambdas = {}

        # Validate Answers Lambda
        lambdas['validate_answers'] = _lambda.Function(
            self, "ValidateAnswersLambda",
            function_name="visamate-validate-answers",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="validate_answers.lambda_handler",
            code=_lambda.Code.from_asset("src/lambdas"),
            memory_size=256,
            timeout=Duration.seconds(30),
            role=lambda_role,
            environment={
                "TABLE_ANSWERS": "visamate-ai-wizardanswers",
                "AWS_REGION": "us-east-1"
            }
        )

        # OCR Task Lambda (reference existing)
        lambdas['ocr_task'] = _lambda.Function.from_function_name(
            self, "ExistingOCRLambda",
            function_name="visamate-ocr-handler"
        )

        # Eligibility Task Lambda
        lambdas['eligibility_task'] = _lambda.Function(
            self, "EligibilityTaskLambda",
            function_name="visamate-eligibility-check",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="eligibility_check.lambda_handler",
            code=_lambda.Code.from_asset("src/lambdas"),
            memory_size=256,
            timeout=Duration.seconds(30),
            role=lambda_role,
            environment={
                "TABLE_ANSWERS": "visamate-ai-wizardanswers",
                "TABLE_USERS": "visamate-ai-users",
                "AWS_REGION": "us-east-1"
            }
        )

        # Form Fill Task Lambda
        lambdas['form_fill_task'] = _lambda.Function(
            self, "FormFillTaskLambda",
            function_name="visamate-form-fill",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="form_fill.lambda_handler",
            code=_lambda.Code.from_asset("src/lambdas"),
            memory_size=512,
            timeout=Duration.seconds(60),
            role=lambda_role,
            environment={
                "TABLE_ANSWERS": "visamate-ai-wizardanswers",
                "TABLE_DOCS": "visamate-ai-documents",
                "BUCKET_DRAFTS": "visamate-documents/drafts",
                "AWS_REGION": "us-east-1"
            }
        )

        return lambdas

    def _create_visa_wizard_workflow(self) -> sfn.StateMachine:
        """Create the Visa Wizard Express workflow."""
        
        # Define workflow steps
        
        # Step 1: Validate Answers
        validate_answers_task = tasks.LambdaInvoke(
            self, "ValidateAnswers",
            lambda_function=self.lambdas['validate_answers'],
            payload=sfn.TaskInput.from_object({
                "user_id.$": "$.user_id",
                "session_id.$": "$.session_id",
                "step": "validate_answers"
            }),
            result_path="$.validation_result"
        )

        # Step 2: Wait for Documents (Choice State)
        wait_for_docs = sfn.Wait(
            self, "WaitForDocuments",
            time=sfn.WaitTime.duration(Duration.minutes(1))
        )

        # Check if documents are uploaded
        check_documents = sfn.Choice(self, "CheckDocuments")
        
        # Step 3: OCR Task
        ocr_task = tasks.LambdaInvoke(
            self, "OCRTask",
            lambda_function=self.lambdas['ocr_task'],
            payload=sfn.TaskInput.from_object({
                "user_id.$": "$.user_id",
                "session_id.$": "$.session_id",
                "step": "ocr_processing"
            }),
            result_path="$.ocr_result"
        )

        # Step 4: Eligibility Check
        eligibility_task = tasks.LambdaInvoke(
            self, "EligibilityTask",
            lambda_function=self.lambdas['eligibility_task'],
            payload=sfn.TaskInput.from_object({
                "user_id.$": "$.user_id",
                "session_id.$": "$.session_id",
                "answers.$": "$.validation_result.answers",
                "ocr_data.$": "$.ocr_result.mapped_data",
                "step": "eligibility_check"
            }),
            result_path="$.eligibility_result"
        )

        # Step 5: Form Fill Task
        form_fill_task = tasks.LambdaInvoke(
            self, "FormFillTask",
            lambda_function=self.lambdas['form_fill_task'],
            payload=sfn.TaskInput.from_object({
                "user_id.$": "$.user_id",
                "session_id.$": "$.session_id",
                "answers.$": "$.validation_result.answers",
                "ocr_data.$": "$.ocr_result.mapped_data",
                "eligibility.$": "$.eligibility_result.eligible",
                "step": "form_fill"
            }),
            result_path="$.form_fill_result"
        )

        # Success state
        success_state = sfn.Succeed(
            self, "WorkflowComplete",
            comment="Visa application workflow completed successfully"
        )

        # Failure state
        failure_state = sfn.Fail(
            self, "WorkflowFailed",
            comment="Visa application workflow failed"
        )

        # Error handling
        retry_policy = sfn.Retry(
            errors=["Lambda.ServiceException", "Lambda.AWSLambdaException"],
            interval=Duration.seconds(2),
            max_attempts=3,
            backoff_rate=2.0
        )

        catch_policy = sfn.Catch(
            errors=["States.ALL"],
            next=failure_state,
            result_path="$.error"
        )

        # Apply error handling to all Lambda tasks
        for task in [validate_answers_task, ocr_task, eligibility_task, form_fill_task]:
            task.add_retry(retry_policy)
            task.add_catch(catch_policy)

        # Define the workflow chain
        documents_ready_condition = sfn.Condition.boolean_equals("$.documents_ready", True)
        
        workflow_definition = validate_answers_task.next(
            check_documents
            .when(
                documents_ready_condition,
                ocr_task.next(
                    eligibility_task.next(
                        form_fill_task.next(success_state)
                    )
                )
            )
            .otherwise(
                wait_for_docs.next(check_documents)
            )
        )

        # Create CloudWatch log group for the state machine
        log_group = logs.LogGroup(
            self, "VisaWizardWorkflowLogs",
            log_group_name="/aws/stepfunctions/visa-wizard-workflow",
            retention=logs.RetentionDays.ONE_WEEK
        )

        # Create the state machine
        state_machine = sfn.StateMachine(
            self, "VisaWizardFlowExpress",
            state_machine_name="VisaWizardFlowExpress",
            definition=workflow_definition,
            state_machine_type=sfn.StateMachineType.EXPRESS,
            logs=sfn.LogOptions(
                destination=log_group,
                level=sfn.LogLevel.ALL
            ),
            tracing_enabled=True
        )

        # Grant permissions to invoke Lambda functions
        for lambda_func in self.lambdas.values():
            lambda_func.grant_invoke(state_machine)

        return state_machine

    def _create_outputs(self) -> None:
        """Create CloudFormation outputs."""
        
        CfnOutput(
            self, "StateMachineArn",
            value=self.state_machine.state_machine_arn,
            description="Visa Wizard Step Function State Machine ARN"
        )

        CfnOutput(
            self, "StateMachineName",
            value=self.state_machine.state_machine_name,
            description="Visa Wizard Step Function State Machine Name"
        )

        for name, lambda_func in self.lambdas.items():
            if hasattr(lambda_func, 'function_arn'):
                CfnOutput(
                    self, f"{name.title()}LambdaArn",
                    value=lambda_func.function_arn,
                    description=f"{name.title()} Lambda Function ARN"
                ) 