# nossis-docs, serverless hosting for static, private web sites that
# works like GitHub Pages
#
# Copyright (C) 2024  Matthew X. Economou
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public
# License along with this program.  If not, see
# <https://www.gnu.org/licenses/>.

"""Configure test fixtures (mocks)."""

import os
import random
import string
from datetime import UTC, datetime

import boto3
import pytest
from faker import Faker
from moto import mock_aws
from mypy_boto3_cloudfront import CloudFrontClient
from mypy_boto3_cloudfront.type_defs import CreateDistributionResultTypeDef


@pytest.fixture
def _aws_credentials(socket_disabled: None) -> None:
    """Avoid mutating real AWS infrastructure by overwriting the
    relevant process environment variables.

    :param socket_disabled: Disables network access via pytest-socket.

    """

    for envvar in [
        "AWS_ACCESS_KEY_ID",
        "AWS_DEFAULT_REGION",
        "AWS_REGION",
        "AWS_SECRET_ACCESS_KEY",
        "AWS_SECURITY_TOKEN",
        "AWS_SESSION_TOKEN",
    ]:
        # A random string guarantees this never results in anything
        # that could possibly be real.
        os.environ[envvar] = "".join(random.sample(string.ascii_letters, 8))

    # This can't overwrite $AWS_PROFILE with nonsense because botocore
    # will try to load that configuration profile, so remove it from
    # the process environment entirely.
    if "AWS_PROFILE" in os.environ:
        del os.environ["AWS_PROFILE"]

    os.environ["MOTO_ALLOW_NONEXISTENT_REGION"] = "True"


@pytest.fixture
def cloudfront(_aws_credentials: None) -> CloudFrontClient:
    """Mock up a CloudFront client.

    :param _aws_credentials: Blocks access to real AWS resources.
    :return: A CloudFront client connected to a mock AWS account.

    """

    with mock_aws():
        yield boto3.client("cloudfront")


@pytest.fixture
def distribution(
    faker: Faker, cloudfront: CloudFrontClient
) -> CreateDistributionResultTypeDef:
    """Mock up a CloudFront distribution.

    :param faker: A fake data generator.
    :param cloudfront: A CloudFront client connected to a mock AWS
        account.
    :return: Information about the CloudFront distribution.

    """

    # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/cloudfront/client/create_distribution.html
    return cloudfront.create_distribution(
        DistributionConfig={
            "CallerReference": datetime.now(UTC).isoformat(),
            "DefaultRootObject": "index.html",
            # TODO: Get content from a mock S3 bucket.
            "Origins": {
                "Quantity": 1,
                "Items": [
                    {
                        "Id": (origin_id := "test-origin"),
                        "DomainName": faker.hostname(),
                        "CustomOriginConfig": {
                            "HTTPPort": 80,
                            "HTTPSPort": 443,
                            "OriginProtocolPolicy": "https-only",
                            "OriginSslProtocols": {"Quantity": 1, "Items": ["TLSv1.2"]},
                        },
                    },
                ],
            },
            "DefaultCacheBehavior": {
                "TargetOriginId": origin_id,
                "ViewerProtocolPolicy": "redirect-to-https",
                "AllowedMethods": {
                    "Quantity": 2,
                    "Items": ["GET", "HEAD"],
                    "CachedMethods": {
                        "Quantity": 2,
                        "Items": ["GET", "HEAD"],
                    },
                },
                "Compress": True,
                "CachePolicyId": "658327ea-f89d-4fab-a63d-7e88639e58f6",
                "OriginRequestPolicyId": "acba4595-bd28-49b8-b9fe-13317c0390fa",
                "ResponseHeadersPolicyId": "67f7725c-6f97-4210-82d7-5512b31e9d03",
            },
            "CustomErrorResponses": {
                "Quantity": len(
                    custom_error_responses := [
                        {
                            "ErrorCode": r,
                            "ResponseCode": str(r),
                            "ResponsePagePath": "/error.html",
                        }
                        for r in [400, 403, 404, 405, 414, 416, 500, 501, 502, 503, 504]
                    ]
                ),
                "Items": custom_error_responses,
            },
            "Comment": "Test Fixture",
            "Logging": {
                "Enabled": False,
                "IncludeCookies": False,
                "Bucket": "",
                "Prefix": "",
            },
            "PriceClass": "PriceClass_100",
            "Enabled": True,
            "ViewerCertificate": {
                "CloudFrontDefaultCertificate": True,
                "MinimumProtocolVersion": "TLSv1.2_2021",
            },
            "Restrictions": {
                "GeoRestriction": {
                    "RestrictionType": "none",
                    "Quantity": 0,
                    "Items": [],
                }
            },
            "IsIPV6Enabled": True,
            "Staging": False,
        }
    )
