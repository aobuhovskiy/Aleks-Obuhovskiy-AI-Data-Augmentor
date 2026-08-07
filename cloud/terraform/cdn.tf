# Super Extra Challenge: S3 + CloudFront CDN
# Publishes the final augmented spreadsheet through a secure CloudFront distribution.

data "aws_caller_identity" "cdn_current" {}

resource "aws_s3_bucket" "cdn_output" {
  bucket = "ai-data-augmentor-output-${data.aws_caller_identity.cdn_current.account_id}"

  tags = {
    Project = "AI Data Augmentor"
    Purpose = "CDN output"
  }
}

resource "aws_s3_bucket_ownership_controls" "cdn_output" {
  bucket = aws_s3_bucket.cdn_output.id

  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

resource "aws_s3_bucket_public_access_block" "cdn_output" {
  bucket = aws_s3_bucket.cdn_output.id

  block_public_acls       = true
  ignore_public_acls      = true
  block_public_policy     = true
  restrict_public_buckets = true
}

resource "aws_cloudfront_origin_access_control" "cdn_output" {
  name                              = "ai-data-augmentor-output-oac"
  description                       = "CloudFront access to private AI Data Augmentor S3 output bucket"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

resource "aws_cloudfront_distribution" "cdn_output" {
  enabled         = true
  is_ipv6_enabled = true
  comment         = "AI Data Augmentor output CDN"
  price_class     = "PriceClass_100"

  origin {
    domain_name              = aws_s3_bucket.cdn_output.bucket_regional_domain_name
    origin_id                = "ai-data-augmentor-s3-origin"
    origin_access_control_id = aws_cloudfront_origin_access_control.cdn_output.id

    s3_origin_config {
      origin_access_identity = ""
    }
  }

  default_cache_behavior {
    target_origin_id       = "ai-data-augmentor-s3-origin"
    viewer_protocol_policy = "redirect-to-https"

    allowed_methods = ["GET", "HEAD"]
    cached_methods  = ["GET", "HEAD"]
    compress        = true

    forwarded_values {
      query_string = false

      cookies {
        forward = "none"
      }
    }

    min_ttl     = 0
    default_ttl = 3600
    max_ttl     = 86400
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
  }

  tags = {
    Project = "AI Data Augmentor"
    Purpose = "CDN output"
  }
}

data "aws_iam_policy_document" "cdn_output" {
  statement {
    sid    = "AllowCloudFrontReadOnly"
    effect = "Allow"

    actions = [
      "s3:GetObject"
    ]

    resources = [
      "${aws_s3_bucket.cdn_output.arn}/*"
    ]

    principals {
      type        = "Service"
      identifiers = ["cloudfront.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "AWS:SourceArn"
      values   = [aws_cloudfront_distribution.cdn_output.arn]
    }
  }
}

resource "aws_s3_bucket_policy" "cdn_output" {
  bucket = aws_s3_bucket.cdn_output.id
  policy = data.aws_iam_policy_document.cdn_output.json

  depends_on = [
    aws_s3_bucket_public_access_block.cdn_output
  ]
}

output "cdn_bucket_name" {
  description = "Private S3 bucket that stores the published output"
  value       = aws_s3_bucket.cdn_output.bucket
}

output "cloudfront_domain_name" {
  description = "CloudFront CDN domain"
  value       = aws_cloudfront_distribution.cdn_output.domain_name
}

output "cdn_excel_url" {
  description = "CDN URL for the augmented Excel workbook after upload"
  value       = "https://${aws_cloudfront_distribution.cdn_output.domain_name}/augmented-companies.xlsx"
}
