"""OpenAPI/Swagger specification for API documentation."""
from flask import Blueprint, jsonify
from src.api.auth import optional_api_key

openapi_bp = Blueprint("openapi", __name__, url_prefix="/api/docs")


@openapi_bp.route("/openapi.json", methods=["GET"])
@optional_api_key
def openapi_spec():
    """OpenAPI 3.0 specification."""
    spec = {
        "openapi": "3.0.0",
        "info": {
            "title": "Research R&D Alpha API",
            "version": "1.0.0",
            "description": "API for analyzing SEC filings and R&D factors",
            "contact": {
                "name": "API Support",
                "email": "support@example.com"
            }
        },
        "servers": [
            {
                "url": "http://localhost:8055",
                "description": "Development server"
            },
            {
                "url": "https://api.example.com",
                "description": "Production server"
            }
        ],
        "components": {
            "securitySchemes": {
                "ApiKeyAuth": {
                    "type": "apiKey",
                    "in": "header",
                    "name": "X-API-Key"
                },
                "BearerAuth": {
                    "type": "http",
                    "scheme": "bearer",
                    "bearerFormat": "JWT"
                }
            }
        },
        "paths": {
            "/api/health": {
                "get": {
                    "summary": "Health check",
                    "tags": ["Health"],
                    "responses": {
                        "200": {
                            "description": "Service is healthy",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "status": {"type": "string", "example": "healthy"}
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            },
            "/api/health/detailed": {
                "get": {
                    "summary": "Detailed health check",
                    "tags": ["Health"],
                    "responses": {
                        "200": {
                            "description": "Service is healthy with dependencies",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "status": {"type": "string"},
                                            "timestamp": {"type": "string"},
                                            "dependencies": {
                                                "type": "object",
                                                "properties": {
                                                    "database": {"type": "object"}
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            },
            "/api/companies": {
                "get": {
                    "summary": "List all companies",
                    "tags": ["Companies"],
                    "responses": {
                        "200": {
                            "description": "List of companies",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "array",
                                        "items": {
                                            "type": "object",
                                            "properties": {
                                                "id": {"type": "integer"},
                                                "ticker": {"type": "string"},
                                                "name": {"type": "string"},
                                                "cik": {"type": "string"},
                                                "years_available": {"type": "integer"}
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            },
            "/api/companies/{ticker}": {
                "get": {
                    "summary": "Get company details",
                    "tags": ["Companies"],
                    "parameters": [
                        {
                            "name": "ticker",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"},
                            "description": "Company ticker symbol"
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "Company details",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "company": {"type": "object"},
                                            "years": {"type": "array"},
                                            "price_data": {"type": "object"}
                                        }
                                    }
                                }
                            }
                        },
                        "404": {
                            "description": "Company not found"
                        }
                    }
                }
            },
            "/api/factors/rd/summary": {
                "get": {
                    "summary": "Get R&D factors summary",
                    "tags": ["Factors"],
                    "responses": {
                        "200": {
                            "description": "R&D factors summary",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "companies": {"type": "array"}
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            },
            "/api/backtests": {
                "get": {
                    "summary": "List backtest runs",
                    "tags": ["Backtests"],
                    "responses": {
                        "200": {
                            "description": "List of backtest runs"
                        }
                    }
                },
                "post": {
                    "summary": "Run a new backtest",
                    "tags": ["Backtests"],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "factor_id": {"type": "string"},
                                        "universe": {"type": "array", "items": {"type": "string"}},
                                        "start_year": {"type": "integer"},
                                        "end_year": {"type": "integer"}
                                    }
                                }
                            }
                        }
                    },
                    "responses": {
                        "200": {
                            "description": "Backtest started"
                        }
                    }
                }
            },
            "/api/metrics": {
                "get": {
                    "summary": "Prometheus metrics",
                    "tags": ["Monitoring"],
                    "responses": {
                        "200": {
                            "description": "Prometheus metrics in text format",
                            "content": {
                                "text/plain": {
                                    "schema": {"type": "string"}
                                }
                            }
                        }
                    }
                }
            }
        },
        "tags": [
            {"name": "Health", "description": "Health check endpoints"},
            {"name": "Companies", "description": "Company data endpoints"},
            {"name": "Factors", "description": "Factor analysis endpoints"},
            {"name": "Backtests", "description": "Backtesting endpoints"},
            {"name": "Monitoring", "description": "Monitoring and metrics endpoints"}
        ]
    }
    
    return jsonify(spec)

