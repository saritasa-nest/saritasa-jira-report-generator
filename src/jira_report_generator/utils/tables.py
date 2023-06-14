from typing import List

from pandas import DataFrame

from .colors import get_danger_color_class
from .tags import TD


def calculate_issues_count(component_issues: DataFrame) -> int:
    """Calculate issues count for component."""
    return len(component_issues)


def calculate_component_estimate(component_issues: DataFrame) -> float:
    """Calculate component estimate."""
    return (
        .0 if component_issues.empty
        else round(component_issues.estimate.sum(), 1)
    )


def calculate_component_spent(component_issues: DataFrame) -> float:
    """Calculate component spent."""
    return (
        .0 if component_issues.empty
        else round(component_issues.spent.sum(), 1)
    )


def calculate_component_left(
    component_issues: DataFrame,
    component_estimate: float,
    component_spent: float,
) -> float:
    """Calculate component left."""
    return (
        .0 if component_issues.empty
        else round(component_estimate - component_spent, 1)
    )


def generate_component_columns(df: DataFrame, components: list) -> List[TD]:
    columns = []

    for component in components:
        default = ""
        component_issues = df[
            df["components"].apply(lambda x: component in x)
        ]

        issues_count = calculate_issues_count(component_issues)
        if issues_count:
            default = 0
        columns.append(TD(str(issues_count or default)))

        component_estimate = calculate_component_estimate(component_issues)
        columns.append(TD(str(component_estimate or default)))

        component_spent = calculate_component_spent(component_issues)
        columns.append(TD(
            str(component_spent or default),
            **{
                "class": get_danger_color_class(
                    component_spent > component_estimate,
                ),
            },
        ))

        component_left = calculate_component_left(
            component_issues,
            component_estimate,
            component_spent,
        )
        columns.append(TD(str(component_left or default)))

    return columns
