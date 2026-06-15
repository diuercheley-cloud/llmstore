from app.schemas.backup import BackupManifest


class RestorePlanner:
    @staticmethod
    def create_plan(manifest: BackupManifest) -> list[str]:
        """
        Generates a sequence of restoration steps based on the manifest.
        """
        plan = []
        # Basic restoration plan based on components
        for component in manifest.components:
            plan.append(f"Restore {component.name} from {component.file_name}")

        # We could add more complex logic here if there are dependencies between components
        return plan
