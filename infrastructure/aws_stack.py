"""
AWS Infrastructure Stack for VisaMate AI platform.
Optimized for AWS Free Tier services with production-ready architecture.
"""

from aws_cdk import (
    Stack,
    Duration,
    RemovalPolicy,
    aws_lambda as _lambda,
    aws_apigateway as apigateway,
    aws_cognito as cognito,
    aws_dynamodb as dynamodb,
    aws_s3 as s3,
    aws_iam as iam,
    aws_logs as logs,
    aws_cloudwatch as cloudwatch,
    aws_events as events,
    aws_events_targets as targets,
    aws_sqs as sqs,
    aws_sns as sns,
    CfnOutput
)
from constructs import Construct


class VisaMateAWSStack(Stack):
    """Main AWS infrastructure stack for VisaMate AI platform."""

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create Cognito User Pool for authentication
        self.user_pool = self._create_user_pool()
        
        # Create DynamoDB tables
        self.tables = self._create_dynamodb_tables()
        
        # Create S3 buckets
        self.buckets = self._create_s3_buckets()
        
        # Create Lambda functions
        self.lambdas = self._create_lambda_functions()
        
        # Create API Gateway
        self.api = self._create_api_gateway()
        
        # Create SQS queues for background processing
        self.queues = self._create_sqs_queues()
        
        # Create CloudWatch monitoring
        self._create_monitoring()
        
        # Output important resource ARNs
        self._create_outputs()

    def _create_user_pool(self) -> cognito.UserPool:
        """Create Cognito User Pool for authentication."""
        user_pool = cognito.UserPool(
            self, "VisaMateUserPool",
            user_pool_name="visamate-users",
            self_sign_up_enabled=True,
            sign_in_case_sensitive=False,
            sign_in_aliases=cognito.SignInAliases(
                email=True,
                phone=True,
                username=True
            ),
            auto_verify=cognito.AutoVerifiedAttrs(email=True),
            password_policy=cognito.PasswordPolicy(
                min_length=8,
                require_lowercase=True,
                require_uppercase=True,
                require_digits=True,
                require_symbols=True
            ),
            account_recovery=cognito.AccountRecovery.EMAIL_ONLY,
            removal_policy=RemovalPolicy.DESTROY,
            # Free tier: up to 50,000 MAUs
            user_verification=cognito.UserVerificationConfig(
                email_subject="VisaMate - Verify your email",
                email_body="Welcome to VisaMate! Your verification code is {####}",
                email_style=cognito.VerificationEmailStyle.CODE
            )
        )

        # Add user pool client
        user_pool_client = cognito.UserPoolClient(
            self, "VisaMateUserPoolClient",
            user_pool=user_pool,
            auth_flows=cognito.AuthFlow(
                user_password=True,
                user_srp=True,
                admin_user_password=True
            ),
            o_auth=cognito.OAuthSettings(
                flows=cognito.OAuthFlows(
                    authorization_code_grant=True,
                    implicit_code_grant=True
                ),
                scopes=[
                    cognito.OAuthScope.EMAIL,
                    cognito.OAuthScope.OPENID,
                    cognito.OAuthScope.PROFILE
                ],
                callback_urls=["http://localhost:3000/callback"],
                logout_urls=["http://localhost:3000/logout"]
            ),
            generate_secret=False  # For frontend applications
        )

        return user_pool

    def _create_dynamodb_tables(self) -> dict:
        """Create DynamoDB tables for the application."""
        tables = {}

        # User profiles table
        tables['users'] = dynamodb.Table(
            self, "UsersTable",
            table_name="visamate-users",
            partition_key=dynamodb.Attribute(
                name="user_id",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,  # Free tier friendly
            removal_policy=RemovalPolicy.DESTROY,
            point_in_time_recovery=False,  # Disable for free tier
            stream=dynamodb.StreamViewType.NEW_AND_OLD_IMAGES
        )

        # Wizard sessions table
        tables['wizard_sessions'] = dynamodb.Table(
            self, "WizardSessionsTable",
            table_name="visamate-wizard-sessions",
            partition_key=dynamodb.Attribute(
                name="session_id",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="user_id",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY,
            time_to_live_attribute="expires_at"
        )

        # SOP documents table
        tables['sop_documents'] = dynamodb.Table(
            self, "SOPDocumentsTable",
            table_name="visamate-sop-documents",
            partition_key=dynamodb.Attribute(
                name="document_id",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="user_id",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY
        )

        # Application tracking table
        tables['applications'] = dynamodb.Table(
            self, "ApplicationsTable",
            table_name="visamate-applications",
            partition_key=dynamodb.Attribute(
                name="application_id",
                type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="user_id",
                type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=RemovalPolicy.DESTROY
        )

        return tables

    def _create_s3_buckets(self) -> dict:
        """Create S3 buckets for document storage."""
        buckets = {}

        # Documents bucket
        buckets['documents'] = s3.Bucket(
            self, "DocumentsBucket",
            bucket_name="visamate-documents-prod",
            versioned=False,  # Disable for free tier
            public_read_access=False,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=RemovalPolicy.DESTROY,
            lifecycle_rules=[
                s3.LifecycleRule(
                    id="DeleteOldVersions",
                    enabled=True,
                    expiration=Duration.days(365),  # Free tier: 5GB storage
                    noncurrent_version_expiration=Duration.days(30)
                )
            ],
            cors=[
                s3.CorsRule(
                    allowed_methods=[
                        s3.HttpMethods.GET,
                        s3.HttpMethods.POST,
                        s3.HttpMethods.PUT
                    ],
                    allowed_origins=["*"],
                    allowed_headers=["*"],
                    max_age=3000
                )
            ]
        )

        # SOP templates bucket
        buckets['templates'] = s3.Bucket(
            self, "TemplatesBucket",
            bucket_name="visamate-templates-prod",
            versioned=False,
            public_read_access=False,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy=RemovalPolicy.DESTROY
        )

        return buckets

    def _create_lambda_functions(self) -> dict:
        """Create Lambda functions for the application."""
        lambdas = {}

        # Common Lambda role
        lambda_role = iam.Role(
            self, "LambdaExecutionRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole")
            ]
        )

        # Add permissions for DynamoDB
        for table in self.tables.values():
            table.grant_read_write_data(lambda_role)

        # Add permissions for S3
        for bucket in self.buckets.values():
            bucket.grant_read_write(lambda_role)

        # SOP Generator Lambda
        lambdas['sop_generator'] = _lambda.Function(
            self, "SOPGeneratorFunction",
            function_name="visamate-sop-generator",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="lambda_function.lambda_handler",
            code=_lambda.Code.from_asset("src/lambdas/sop_generator"),
            timeout=Duration.minutes(5),  # Free tier: 15 minutes max
            memory_size=512,  # Free tier: up to 512MB
            role=lambda_role,
            environment={
                "GEMINI_API_KEY": "{{resolve:secretsmanager:visamate/gemini:SecretString:api_key}}",
                "DYNAMODB_TABLE_PREFIX": "visamate",
                "S3_BUCKET_DOCUMENTS": self.buckets['documents'].bucket_name
            },
            log_retention=logs.RetentionDays.ONE_WEEK
        )

        # Document Processor Lambda
        lambdas['document_processor'] = _lambda.Function(
            self, "DocumentProcessorFunction",
            function_name="visamate-document-processor",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="lambda_function.lambda_handler",
            code=_lambda.Code.from_asset("src/lambdas/document_processor"),
            timeout=Duration.minutes(3),
            memory_size=256,
            role=lambda_role,
            environment={
                "S3_BUCKET_DOCUMENTS": self.buckets['documents'].bucket_name,
                "DYNAMODB_TABLE_PREFIX": "visamate"
            }
        )

        # Wizard API Lambda
        lambdas['wizard_api'] = _lambda.Function(
            self, "WizardAPIFunction",
            function_name="visamate-wizard-api",
            runtime=_lambda.Runtime.PYTHON_3_11,
            handler="lambda_function.lambda_handler",
            code=_lambda.Code.from_asset("src/lambdas/wizard_api"),
            timeout=Duration.seconds(30),
            memory_size=256,
            role=lambda_role,
            environment={
                "COGNITO_USER_POOL_ID": self.user_pool.user_pool_id,
                "DYNAMODB_TABLE_PREFIX": "visamate"
            }
        )

        return lambdas

    def _create_api_gateway(self) -> apigateway.RestApi:
        """Create API Gateway for the application."""
        api = apigateway.RestApi(
            self, "VisaMateAPI",
            rest_api_name="visamate-api",
            description="VisaMate AI API Gateway",
            default_cors_preflight_options=apigateway.CorsOptions(
                allow_origins=apigateway.Cors.ALL_ORIGINS,
                allow_methods=apigateway.Cors.ALL_METHODS,
                allow_headers=["Content-Type", "Authorization"]
            ),
            deploy_options=apigateway.StageOptions(
                stage_name="prod",
                throttling_rate_limit=100,  # Free tier: 10,000 requests per month
                throttling_burst_limit=50
            )
        )

        # Create Cognito authorizer
        auth = apigateway.CognitoUserPoolsAuthorizer(
            self, "VisaMateAuthorizer",
            cognito_user_pools=[self.user_pool]
        )

        # V1 API routes
        v1 = api.root.add_resource("v1")

        # Wizard routes
        wizard = v1.add_resource("wizard")
        wizard.add_method(
            "POST",
            apigateway.LambdaIntegration(self.lambdas['wizard_api']),
            authorizer=auth
        )
        wizard.add_method(
            "GET",
            apigateway.LambdaIntegration(self.lambdas['wizard_api']),
            authorizer=auth
        )

        # SOP routes
        sop = v1.add_resource("sop")
        sop.add_method(
            "POST",
            apigateway.LambdaIntegration(self.lambdas['sop_generator']),
            authorizer=auth
        )

        # Documents routes
        documents = v1.add_resource("documents")
        documents.add_method(
            "POST",
            apigateway.LambdaIntegration(self.lambdas['document_processor']),
            authorizer=auth
        )

        return api

    def _create_sqs_queues(self) -> dict:
        """Create SQS queues for background processing."""
        queues = {}

        # SOP generation queue
        queues['sop_generation'] = sqs.Queue(
            self, "SOPGenerationQueue",
            queue_name="visamate-sop-generation",
            visibility_timeout=Duration.minutes(6),
            message_retention_period=Duration.days(14),  # Free tier: 1M requests/month
            dead_letter_queue=sqs.DeadLetterQueue(
                max_receive_count=3,
                queue=sqs.Queue(
                    self, "SOPGenerationDLQ",
                    queue_name="visamate-sop-generation-dlq"
                )
            )
        )

        # Document processing queue
        queues['document_processing'] = sqs.Queue(
            self, "DocumentProcessingQueue",
            queue_name="visamate-document-processing",
            visibility_timeout=Duration.minutes(4),
            message_retention_period=Duration.days(14)
        )

        # Connect queues to Lambda functions
        self.lambdas['sop_generator'].add_event_source(
            _lambda.SqsEventSource(queues['sop_generation'])
        )
        
        self.lambdas['document_processor'].add_event_source(
            _lambda.SqsEventSource(queues['document_processing'])
        )

        return queues

    def _create_monitoring(self) -> None:
        """Create CloudWatch monitoring and alarms."""
        # Create SNS topic for alerts
        alert_topic = sns.Topic(
            self, "VisaMateAlerts",
            topic_name="visamate-alerts"
        )

        # Lambda error alarms
        for name, function in self.lambdas.items():
            cloudwatch.Alarm(
                self, f"{name}ErrorAlarm",
                metric=function.metric_errors(),
                threshold=5,
                evaluation_periods=2,
                alarm_description=f"Lambda function {name} error rate"
            ).add_alarm_action(
                cloudwatch.SnsAction(alert_topic)
            )

        # API Gateway 4xx/5xx alarms
        cloudwatch.Alarm(
            self, "APIGateway4xxAlarm",
            metric=self.api.metric_client_error(),
            threshold=10,
            evaluation_periods=2,
            alarm_description="API Gateway 4xx errors"
        ).add_alarm_action(
            cloudwatch.SnsAction(alert_topic)
        )

        # DynamoDB throttle alarms
        for name, table in self.tables.items():
            cloudwatch.Alarm(
                self, f"{name}ThrottleAlarm",
                metric=table.metric_throttled_requests(),
                threshold=1,
                evaluation_periods=1,
                alarm_description=f"DynamoDB table {name} throttling"
            ).add_alarm_action(
                cloudwatch.SnsAction(alert_topic)
            )

    def _create_outputs(self) -> None:
        """Create CloudFormation outputs."""
        CfnOutput(
            self, "UserPoolId",
            value=self.user_pool.user_pool_id,
            description="Cognito User Pool ID"
        )

        CfnOutput(
            self, "APIGatewayURL",
            value=self.api.url,
            description="API Gateway URL"
        )

        CfnOutput(
            self, "DocumentsBucket",
            value=self.buckets['documents'].bucket_name,
            description="S3 Documents Bucket Name"
        )

        for name, table in self.tables.items():
            CfnOutput(
                self, f"{name.title()}TableName",
                value=table.table_name,
                description=f"DynamoDB {name} table name"
            ) 