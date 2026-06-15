from control_plane.app.services.config_service import BaseAppConfig


def generate_inventory():
    print("# Flags Inventory")
    print("| Flag | Default | Type | Alias |")
    print("|------|---------|------|-------|")

    for field_name, field_info in BaseAppConfig.model_fields.items():
        default = field_info.default
        alias = field_info.alias
        type_ = field_info.annotation

        print(f"| {field_name} | {default} | {type_} | {alias} |")


if __name__ == "__main__":
    generate_inventory()
