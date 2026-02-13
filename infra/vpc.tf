resource "aws_security_group" "lambda" {
  name_prefix = "cde-recommend-lambda-"
  description = "Security group for CDE recommendation Lambda"
  vpc_id      = var.vpc_id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Allow all outbound (RDS + OpenAI API)"
  }

  tags = {
    Name        = "cde-recommend-lambda-${var.environment}"
    Environment = var.environment
  }
}
