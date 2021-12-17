from app.model.osdu_model import WellboreTrajectory110

from .unique import get_unique_ids


class DuplicatedStationProperties(RuntimeError):
    """raised if all curveID values are not unique"""


def check_trajectory_consistency(traj: WellboreTrajectory110):
    """Check if trajectory is consistent.

    Each station in data.AvailableTrajectoryStationProperties must have a unique name.

    Args:
        traj (WellboreTrajectory110): trajectory object to be verified

    Returns:

    Raises:
        DuplicatedStationProperties: All StationProperties are not unique.
    """
    if not traj.data or not traj.data.AvailableTrajectoryStationProperties:
        return

    curve_ids, duplicated_error = get_unique_ids(
        traj.data.AvailableTrajectoryStationProperties, "TrajectoryStationPropertyTypeID"
    )

    if duplicated_error:
        raise DuplicatedStationProperties()
