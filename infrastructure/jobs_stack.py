"""
AWS Jobs Stack for VisaMate AI OCR Processing Pipeline.
Imports existing resources and creates Lambda functions for document processing.
"""

from aws_cdk import (
    Stack,
    Duration,
    aws_lambda as _lambda,
    aws_s3 as s3,
    aws_sqs as sqs,
    aws_sns as sns,
    aws_iam as iam,
    aws_lambda_event_sources as lambda_event_sources,
    aws_events as events,
    aws_events_targets as targets,
    aws_s3_notifications as s3n,
    CfnOutput
)
from constructs import Construct


class VisaMateJobsStack(Stack):
    """Jobs stack for OCR processing pipeline."""

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Import existing S3 bucket
        self.documents_bucket = s3.Bucket.from_bucket_name(
            self, "ExistingDocumentsBucket",
            bucket_name="visamate-documents"
        )

        # Import existing SQS queues
        self.ocr_jobs_queue = sqs.Queue.from_queue_attributes(
            self, "ExistingOCRJobsQueue",
            queue_arn="arn:aws:sqs:us-east-1:790791784202:ocr-jobs-queue",
            queue_url="https://sqs.us-east-1.amazonaws.com/790791784202/ocr-jobs-queue"
        )

        self.ocr_jobs_dlq = sqs.Queue.from_queue_attributes(
            self, "ExistingOCRJobsDLQ", 
            queue_arn="arn:aws:sqs:us-east-1:790791784202:ocr-jobs-dlq",
            queue_url="https://sqs.us-east-1.amazonaws.com/790791784202/ocr-jobs-dlq"
        )

        # Import existing SNS topic
        self.ocr_complete_topic = sns.Topic.from_topic_arn(
            self, "ExistingOCRCompleteTopic",
            topic_arn="arn:aws:sns:us-east-1:790791784202:ocr-complete-topic"
        )

        # Create OCR Handler Lambda
        self.ocr_handler = self._create_ocr_handler_lambda()
        
        # Create Textract Callback Lambda
        self.textract_callback = self._create_textract_callback_lambda()

        # Set up S3 event notifications to SQS
        self._setup_s3_notifications()

        # Set up SQS as Lambda event source
        self._setup_lambda_event_sources()
        
        # Set up SNS subscriptions
        self._setup_sns_subscriptions()

        # Create outputs
        self._create_outputs()

    def _create_ocr_handler_lambda(self) -> _lambda.Function:
        """Create the OCR handler Lambda function."""
        
        # Create IAM role for OCR Lambda
        ocr_lambda_role = iam.Role(
            self, "OCRLambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole")
            ],
            inline_policies={
                "OCRProcessingPolicy": iam.PolicyDocument(
                    statements=[
                        # S3 permissions
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "s3:GetObject",
                                "s3:GetObjectVersion"
                            ],
                            resources=[
                                f"{self.documents_bucket.bucket_arn}/raw/*"
                            ]
                        ),
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "s3:PutObject",
                                "s3:PutObjectAcl"
                            ],
                            resources=[
                                f"{self.documents_bucket.bucket_arn}/json/*"
                            ]
                        ),
                        # Textract permissions
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "textract:DetectDocumentText",
                                "textract:AnalyzeDocument",
                                "textract:StartDocumentTextDetection",
                                "textract:GetDocumentTextDetection"
                            ],
                            resources=["*"]
                        ),
                        # SNS permissions
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "sns:Publish"
                            ],
                            resources=[
                                self.ocr_complete_topic.topic_arn
                            ]
                        ),
                        # SQS permissions
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "sqs:ReceiveMessage",
                                "sqs:DeleteMessage",
                                "sqs:GetQueueAttributes"
                            ],
                            resources=[
                                self.ocr_jobs_queue.queue_arn,
                                self.ocr_jobs_dlq.queue_arn
                            ]
                        ),
                        # DynamoDB permissions for document metadata
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "dynamodb:GetItem",
                                "dynamodb:PutItem",
                                "dynamodb:UpdateItem"
                            ],
                            resources=[
                                f"arn:aws:dynamodb:us-east-1:790791784202:table/visamate-ai-documents",
                                f"arn:aws:dynamodb:us-east-1:790791784202:table/visamate-ai-wizardanswers"
                            ]
                        )
                    ]
                )
            }
        )

        # Create Lambda function
        ocr_handler = _lambda.Function(
            self, "VisaMateOCRHandler",
            function_name="visamate-ocr-handler",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="ocr_handler.lambda_handler",
            code=_lambda.Code.from_asset("src/lambdas"),
            memory_size=512,
            timeout=Duration.seconds(60),
            role=ocr_lambda_role,
            environment={
                "BUCKET_RAW": "visamate-documents/raw",
                "BUCKET_JSON": "visamate-documents/json",
                "SNS_OCR_TOPIC": "arn:aws:sns:us-east-1:790791784202:ocr-complete-topic",
                "TABLE_DOCS": "visamate-ai-documents",
                "TABLE_ANSWERS": "visamate-ai-wizardanswers",
                "AWS_REGION": "us-east-1"
            },
            dead_letter_queue_enabled=True,
            dead_letter_queue=self.ocr_jobs_dlq
        )

        return ocr_handler

    def _create_textract_callback_lambda(self) -> _lambda.Function:
        """Create the Textract callback Lambda function for async processing."""
        
        # Create IAM role for Textract callback Lambda
        callback_lambda_role = iam.Role(
            self, "TextractCallbackLambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole")
            ],
            inline_policies={
                "TextractCallbackPolicy": iam.PolicyDocument(
                    statements=[
                        # Textract permissions
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "textract:GetDocumentTextDetection"
                            ],
                            resources=["*"]
                        ),
                        # S3 permissions
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "s3:PutObject",
                                "s3:PutObjectAcl"
                            ],
                            resources=[
                                f"{self.documents_bucket.bucket_arn}/json/*"
                            ]
                        ),
                        # SNS permissions
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "sns:Publish"
                            ],
                            resources=[
                                self.ocr_complete_topic.topic_arn
                            ]
                        ),
                        # DynamoDB permissions
                        iam.PolicyStatement(
                            effect=iam.Effect.ALLOW,
                            actions=[
                                "dynamodb:UpdateItem"
                            ],
                            resources=[
                                f"arn:aws:dynamodb:us-east-1:790791784202:table/visamate-ai-documents"
                            ]
                        )
                    ]
                )
            }
        )

        # Create Lambda function
        textract_callback = _lambda.Function(
            self, "VisaMateTextractCallback",
            function_name="visamate-textract-callback",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="textract_callback.lambda_handler",
            code=_lambda.Code.from_asset("src/lambdas"),
            memory_size=256,
            timeout=Duration.seconds(60),
            role=callback_lambda_role,
            environment={
                "BUCKET_JSON": "visamate-documents/json",
                "SNS_OCR_TOPIC": "arn:aws:sns:us-east-1:790791784202:ocr-complete-topic",
                "TABLE_DOCS": "visamate-ai-documents",
                "AWS_REGION": "us-east-1"
            }
        )

        return textract_callback

    def _setup_s3_notifications(self) -> None:
        """Set up S3 event notifications to trigger OCR processing."""
        
        # Add S3 event notification to send messages to SQS when objects are created in raw/ prefix
        self.documents_bucket.add_event_notification(
            s3.EventType.OBJECT_CREATED,
            s3n.SqsDestination(self.ocr_jobs_queue),
            s3.NotificationKeyFilter(prefix="raw/")
        )

    def _setup_lambda_event_sources(self) -> None:
        """Set up SQS as event source for Lambda."""
        
        # Add SQS as event source for OCR Lambda
        self.ocr_handler.add_event_source(
            lambda_event_sources.SqsEventSource(
                queue=self.ocr_jobs_queue,
                batch_size=1,  # Process one document at a time
                max_batching_window=Duration.seconds(5),
                report_batch_item_failures=True
            )
        )

    def _setup_sns_subscriptions(self) -> None:
        """Set up SNS subscriptions for Textract callbacks."""
        
        # Subscribe textract callback Lambda to SNS topic
        # Note: This would be for Textract's built-in SNS notifications
        # The actual subscription would be created when starting async Textract jobs
        
        # For now, we'll add the subscription manually or via the Lambda trigger
        # since Textract sends notifications to a specific topic format
        pass

    def _create_outputs(self) -> None:
        """Create CloudFormation outputs."""
        
        CfnOutput(
            self, "OCRHandlerFunctionName",
            value=self.ocr_handler.function_name,
            description="OCR Handler Lambda Function Name"
        )

        CfnOutput(
            self, "OCRHandlerFunctionArn",
            value=self.ocr_handler.function_arn,
            description="OCR Handler Lambda Function ARN"
        )

        CfnOutput(
            self, "DocumentsBucketName",
            value=self.documents_bucket.bucket_name,
            description="Documents S3 Bucket Name"
        )

        CfnOutput(
            self, "OCRJobsQueueUrl",
            value=self.ocr_jobs_queue.queue_url,
            description="OCR Jobs SQS Queue URL"
        ) 