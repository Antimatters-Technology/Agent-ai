#!/usr/bin/env python3
"""
CDK App for VisaMate AI Infrastructure
"""

import os
import aws_cdk as cdk
from jobs_stack import VisaMateJobsStack
from stepfn_stack import VisaMateStepFunctionStack


app = cdk.App()

# Environment configuration
env = cdk.Environment(
    account=os.getenv('CDK_DEFAULT_ACCOUNT', '790791784202'),
    region=os.getenv('CDK_DEFAULT_REGION', 'us-east-1')
)

# Deploy Jobs Stack (OCR Pipeline)
jobs_stack = VisaMateJobsStack(
    app, 
    "VisaMateJobsStack",
    env=env,
    description="VisaMate AI OCR Processing Pipeline"
)

# Deploy Step Functions Stack (Workflow)
stepfn_stack = VisaMateStepFunctionStack(
    app,
    "VisaMateStepFunctionStack", 
    env=env,
    description="VisaMate AI Visa Wizard Workflow"
)

# Add dependency
stepfn_stack.add_dependency(jobs_stack)

# Add tags
cdk.Tags.of(app).add("Project", "VisaMate-AI")
cdk.Tags.of(app).add("Environment", "Production")
cdk.Tags.of(app).add("Owner", "DevOps-Team")

app.synth() 