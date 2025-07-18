from prowler.lib.check.models import Check, Check_Report_Azure
from prowler.providers.azure.services.app.app_client import app_client


class app_function_application_insights_enabled(Check):
    def execute(self):
        findings = []

        for (
            subscription_name,
            functions,
        ) in app_client.functions.items():
            for function in functions.values():
                if function.enviroment_variables is not None:
                    report = Check_Report_Azure(
                        metadata=self.metadata(), resource=function
                    )
                    report.subscription = subscription_name
                    report.status = "FAIL"
                    report.status_extended = (
                        f"Function {function.name} is not using Application Insights."
                    )

                    if function.enviroment_variables.get(
                        "APPINSIGHTS_INSTRUMENTATIONKEY", None
                    ) or function.enviroment_variables.get(
                        "APPLICATIONINSIGHTS_CONNECTION_STRING", None
                    ):
                        report.status = "PASS"
                        report.status_extended = (
                            f"Function {function.name} is using Application Insights."
                        )

                    findings.append(report)

        return findings
