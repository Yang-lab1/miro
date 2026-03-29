from app.modules.realtime.providers.base import (
    RealtimeAlertExtractionContext,
    RealtimeAlertSpec,
)


class RuleBasedRealtimeAlertAnalyzer:
    def extract_alerts(
        self,
        context: RealtimeAlertExtractionContext,
    ) -> list[RealtimeAlertSpec]:
        lowered = context.normalized_text.lower()
        alerts: list[RealtimeAlertSpec] = []

        if len(context.normalized_text.split(" ")) < 8:
            alerts.append(
                RealtimeAlertSpec(
                    issue_key="underdeveloped_answer",
                    severity="medium",
                    title_text="Answer is too thin",
                    detail_text="The response is too short to move the conversation forward.",
                )
            )

        if (
            context.grounding.country_key == "Japan"
            and context.grounding.meeting_type_key == "first_introduction"
            and any(
                word in lowered
                for word in ("price", "discount", "cheap", "lowest", "budget")
            )
            and len(alerts) < 2
        ):
            detail_text = "This opening risks pushing pricing before trust is established."
            if context.grounding.uploaded_context_summary_en:
                detail_text = (
                    f"{detail_text} It also ignores the uploaded brief: "
                    f"{context.grounding.uploaded_context_summary_en}"
                )
            alerts.append(
                RealtimeAlertSpec(
                    issue_key="premature_pricing_push",
                    severity="high",
                    title_text="Price pressure is too early",
                    detail_text=detail_text,
                )
            )

        if (
            any(word in lowered for word in ("guarantee", "always", "never", "no risk", "100%"))
            and len(alerts) < 2
        ):
            alerts.append(
                RealtimeAlertSpec(
                    issue_key="overclaiming",
                    severity="medium",
                    title_text="Claim sounds too absolute",
                    detail_text="The wording may sound overconfident or hard to defend.",
                )
            )

        return alerts[:2]
