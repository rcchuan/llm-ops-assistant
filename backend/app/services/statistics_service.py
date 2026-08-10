from app.repositories.statistics_repository import StatisticsRepository


class StatisticsService:
    def __init__(self, repository: StatisticsRepository):
        self.repository = repository

    def overview(self) -> dict[str, object]:
        data = self.repository.overview()
        rated = data["helpful_count"] + data["unhelpful_count"]
        operator_count = data["operator_count"]
        return {
            "qa": {
                "total_count": data["total_count"],
                "operator_count": operator_count,
                "converted_count": data["converted_count"],
                "conversion_rate": round(data["converted_count"] / operator_count * 100, 2) if operator_count else None,
            },
            "feedback": {
                "helpful_count": data["helpful_count"],
                "unhelpful_count": data["unhelpful_count"],
                "unrated_count": data["unrated_count"],
                "satisfaction_rate": round(data["helpful_count"] / rated * 100, 2) if rated else None,
            },
            "work_orders": data["work_orders"],
            "knowledge_entries": data["knowledge_entries"],
        }
