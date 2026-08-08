from typing import Any

import mlflow
from log import logger

HAS_MLFLOW = True


class ExperimentTracker:
    def __init__(self, tracking_uri: str = "sqlite:///./mlflow.db", experiment: str = "finagent"):
        try:
            mlflow.set_tracking_uri(tracking_uri)
            mlflow.set_experiment(experiment)
        except Exception as e:
            logger.warning(f"mlflow init failed: {e}")

    def log_backtest(
        self,
        symbol: str,
        params: dict[str, Any],
        metrics: dict[str, Any],
        tags: dict[str, str] | None = None,
    ) -> int | None:
        if not HAS_MLFLOW:
            return None
        try:
            with mlflow.start_run(run_name=f"bt_{symbol.replace('/', '_')}"):
                mlflow.log_params(params)
                mlflow.log_metrics({k: float(v) for k, v in metrics.items() if isinstance(v, (int, float))})
                if tags:
                    mlflow.set_tags(tags)
                run_id = mlflow.active_run().info.run_id if mlflow.active_run() else None
                logger.info(f"mlflow logged run: {run_id}")
                return run_id
        except Exception as e:
            logger.error(f"mlflow log failed: {e}")
            return None

    def list_runs(self, limit: int = 20) -> list[dict[str, Any]]:
        try:
            client = mlflow.tracking.MlflowClient()
            exp = mlflow.get_experiment_by_name("finagent")
            if not exp:
                return []
            runs = client.search_runs(
                experiment_ids=[exp.experiment_id],
                max_results=limit,
                order_by=["start_time DESC"],
            )
            return [
                {
                    "run_id": r.info.run_id,
                    "name": r.info.run_name,
                    "start": r.info.start_time,
                    "metrics": {k: round(v, 4) for k, v in r.data.metrics.items()},
                }
                for r in runs
            ]
        except Exception as e:
            logger.error(f"mlflow list failed: {e}")
            return []