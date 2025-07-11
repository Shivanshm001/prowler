from pydantic.v1 import BaseModel

from prowler.lib.logger import logger
from prowler.providers.gcp.gcp_provider import GcpProvider
from prowler.providers.gcp.lib.service.service import GCPService


class CloudResourceManager(GCPService):
    def __init__(self, provider: GcpProvider):
        super().__init__(__class__.__name__, provider)

        self.bindings = []
        self.cloud_resource_manager_projects = []
        self.organizations = []
        self._get_iam_policy()
        self._get_organizations()

    def _get_iam_policy(self):
        for project_id in self.project_ids:
            try:
                policy = (
                    self.client.projects().getIamPolicy(resource=project_id).execute()
                )
                audit_logging = False
                if policy.get("auditConfigs"):
                    audit_logging = True
                self.cloud_resource_manager_projects.append(
                    Project(id=project_id, audit_logging=audit_logging)
                )
                for binding in policy["bindings"]:
                    self.bindings.append(
                        Binding(
                            role=binding["role"],
                            members=binding["members"],
                            project_id=project_id,
                        )
                    )
            except Exception as error:
                logger.error(
                    f"{self.region} -- {error.__class__.__name__}[{error.__traceback__.tb_lineno}]: {error}"
                )

    def _get_organizations(self):
        try:
            if self.project_ids:
                response = self.client.organizations().search().execute()
                for org in response.get("organizations", []):
                    self.organizations.append(
                        Organization(
                            id=org["name"].split("/")[-1], name=org["displayName"]
                        )
                    )
        except Exception as error:
            logger.error(
                f"{self.region} -- {error.__class__.__name__}[{error.__traceback__.tb_lineno}]: {error}"
            )


class Binding(BaseModel):
    role: str
    members: list
    project_id: str


class Project(BaseModel):
    id: str
    audit_logging: bool


class Organization(BaseModel):
    id: str
    name: str
