import pathlib

import fusion
import yaml
from fusion.rest import ApiException

from utils import get_fusion_config, wait_operation_succeeded, ResourceNameReserved
import getters


def setup_workloads():
    print("Setting up workloads")

    # create an API client with your access Configuration
    config = get_fusion_config()
    client = fusion.ApiClient(config)

    # get needed API clients
    ts = fusion.TenantSpacesApi(api_client=client)
    pg = fusion.PlacementGroupsApi(api_client=client)
    v = fusion.VolumesApi(api_client=client)
    h = fusion.HostAccessPoliciesApi(api_client=client)

    # Load configuration
    with open(pathlib.Path(__file__).parent / "config/workloads.yaml") as file:
        sample_workload = yaml.safe_load(file)

    # Create Tenant-Spaces
    for workload in sample_workload:
        print("Creating tenant space",
              workload["name"], "in tenant", workload["tenant"])
        current_tenant_space = fusion.TenantSpacePost(
            name=workload["name"],
            display_name=workload["display_name"]
        )
        try:
            api_response = ts.create_tenant_space(
                current_tenant_space, workload["tenant"])
            # pprint(api_response)
            wait_operation_succeeded(api_response.id, client, resource_getter=getters.tenant_space_getter(
                ts, workload["tenant"], current_tenant_space.name))
        except ResourceNameReserved as e:
            if not e.resource_exists:
                raise e
        except ApiException as e:
            raise RuntimeError(
                "Exception when calling TenantSpacesApi->create_tenant_space") from e

        # Create Placement Groups
        for placement_group in workload["placement_groups"]:
            print("Creating placement group",
                  placement_group["name"], "in tenant space", current_tenant_space.name, "in tenant", workload["tenant"])
            current_placement_group = fusion.PlacementGroupPost(
                name=placement_group["name"],
                display_name=placement_group["display_name"],
                region=placement_group["region"],
                availability_zone=placement_group["availability_zone"],
                storage_service=placement_group["storage_service"]
            )
            try:
                api_response = pg.create_placement_group(
                    current_placement_group, workload["tenant"], current_tenant_space.name)
                # pprint(api_response)
                wait_operation_succeeded(api_response.id, client, resource_getter=getters.placement_group_getter(
                    pg, workload["tenant"], current_tenant_space.name, current_placement_group.name))
            except ResourceNameReserved as e:
                if not e.resource_exists:
                    raise e
            except ApiException as e:
                raise RuntimeError(
                    "Exception when calling PlacementGroupsApi->create_placement_group") from e

        # Create Host-Access-Policy
        for host_access_policy in workload["host_access_policies"]:
            print("Creating host access policy", host_access_policy["name"])
            current_host_access_policy = fusion.HostAccessPoliciesPost(
                name=host_access_policy["name"],
                display_name=host_access_policy["display_name"],
                iqn=host_access_policy["iqn"],
                personality=host_access_policy["personality"]
            )
            try:
                api_response = h.create_host_access_policy(
                    current_host_access_policy)
                # pprint(api_response)
                wait_operation_succeeded(api_response.id, client, resource_getter=getters.host_access_policy_getter(
                    h, current_host_access_policy.name))
            except ResourceNameReserved as e:
                if not e.resource_exists:
                    raise e
            except ApiException as e:
                raise RuntimeError(
                    "Exception when calling HostAccessPoliciesApi->create_host_access_policy") from e

        # Create Volumes
        for volume in workload["volumes"]:
            print("Creating volume", volume["name"], "in tenant space",
                  current_tenant_space.name, "in tenant", workload["tenant"])
            current_volume = fusion.VolumePost(
                name=volume["name"],
                display_name=volume["display_name"],
                size=volume["size"],
                storage_class=volume["storage_class"],
                placement_group=volume["placement_group"],
                protection_policy=volume.get("protection_policy")
            )
            try:
                api_response = v.create_volume(
                    current_volume, workload["tenant"], current_tenant_space.name)
                # pprint(api_response)
                wait_operation_succeeded(api_response.id, client, resource_getter=getters.volume_getter(
                    v, workload["tenant"], current_tenant_space.name, current_volume.name))
            except ResourceNameReserved as e:
                if not e.resource_exists:
                    raise e
            except ApiException as e:
                raise RuntimeError(
                    "Exception when calling VolumesApi->create_volume") from e

            # Assign Host-Access-Policies to Volume
            print("Updating volume", volume["name"], "with host access policies", volume["host_access_policies"], "in tenant space", current_tenant_space.name, "in tenant",
                  workload["tenant"])
            current_volume_patch = fusion.VolumePatch(
                host_access_policies=fusion.NullableString(
                    volume["host_access_policies"])
            )
            try:
                api_response = v.update_volume(
                    current_volume_patch, workload["tenant"], current_tenant_space.name, current_volume.name)
                # pprint(api_response)
                wait_operation_succeeded(api_response.id, client)
            except ApiException as e:
                raise RuntimeError(
                    "Exception when calling VolumesApi->update_volume") from e

    print("Done setting up workloads!")


if __name__ == '__main__':
    setup_workloads()
