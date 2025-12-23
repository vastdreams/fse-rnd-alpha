"""Backtest API endpoints."""
from flask import Blueprint, jsonify, request
from src.db.connection import db_session_scope
from src.models.orm.backtest_run import BacktestRun
from src.models.orm.backtest import BacktestResult
from src.backtesting.engine import run_backtest
from src.backtesting.specs import BacktestSpec
from src.logging.logger import get_logger

logger = get_logger(__name__)
backtest_api_bp = Blueprint("backtest_api", __name__, url_prefix="/api/backtests")


@backtest_api_bp.route("/", methods=["GET"])
def list_backtests():
    """List all backtest runs."""
    with db_session_scope() as session:
        runs = session.query(BacktestRun).order_by(BacktestRun.created_at.desc()).limit(20).all()
        
        data = [{
            "id": r.id,
            "factor_id": r.factor_id,
            "start_year": r.start_year,
            "end_year": r.end_year,
            "status": r.status,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        } for r in runs]
        
        return jsonify(data)


@backtest_api_bp.route("/<int:run_id>/results", methods=["GET"])
def get_backtest_results(run_id):
    """Get results for a specific backtest run."""
    with db_session_scope() as session:
        results = session.query(BacktestResult).filter_by(
            backtest_run_id=run_id
        ).all()
        
        data = [{
            "formation_year": r.formation_year,
            "bucket": r.bucket,
            "mean_ret": r.mean_ret,
            "t_stat": r.t_stat,
            "n": r.n,
            "sharpe_ratio": r.sharpe_ratio,
        } for r in results]
        
        return jsonify(data)


@backtest_api_bp.route("/run", methods=["POST"])
def run_new_backtest():
    """Run a new backtest."""
    data = request.json
    
    spec = BacktestSpec(
        factor_id=data.get("factor_id", "RND_v1_combined"),
        universe=data.get("universe", ["pilot_top10"]),
        start_year=data.get("start_year", 2020),
        end_year=data.get("end_year", 2023),
        formation_schedule=data.get("formation_schedule", "annual"),
        holding_period_years=data.get("holding_period_years", 1),
        num_buckets=data.get("num_buckets", 10),
    )
    
    try:
        run = run_backtest(spec)
        return jsonify({
            "id": run.id,
            "status": run.status,
            "spec_hash": run.spec_hash,
        })
    except Exception as e:
        logger.error(f"Error running backtest: {e}")
        return jsonify({"error": str(e)}), 500

