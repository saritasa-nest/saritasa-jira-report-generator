from typing import List

from pandas import DataFrame

from .colors import get_danger_color_class
from .tags import TD


def generate_component_columns(df: DataFrame, components: list) -> List[TD]:
    columns = []

    for component in components:
        default = ""
        component_issues = df[
            df["components"].apply(lambda x: component in x)
        ]
        component_estimate = round(component_issues.estimate.sum(), 1)
        component_spent = round(component_issues.spent.sum(), 1)
        component_left = round(component_estimate - component_spent, 1)
        issues_count = len(component_issues)

        if issues_count > 0:
            default = 0

        columns.append(TD(
            issues_count
            if not component_issues.empty
            else default
        ))
        columns.append(TD(
            component_estimate
            if component_estimate
            else default
        ))
        columns.append(TD(
            component_spent
            if component_spent
            else default,
            **{
                "class": get_danger_color_class(
                    component_spent > component_estimate,
                ),
            },
        ))
        columns.append(TD(
            component_left
            if component_left > 0
            else default
        ))

    return columns
