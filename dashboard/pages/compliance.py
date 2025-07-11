# Standard library imports
import csv
import glob
import importlib
import os
import re
import warnings

# Third-party imports
import dash
import pandas as pd
import plotly.express as px
from dash import callback, dcc, html
from dash.dependencies import Input, Output

# Config import
from dashboard.config import (
    encoding_format,
    error_action,
    fail_color,
    folder_path_compliance,
    info_color,
    manual_color,
    pass_color,
)
from dashboard.lib.dropdowns import (
    create_account_dropdown_compliance,
    create_compliance_dropdown,
    create_date_dropdown_compliance,
    create_region_dropdown_compliance,
)
from dashboard.lib.layouts import create_layout_compliance
from prowler.lib.logger import logger

# Suppress warnings
warnings.filterwarnings("ignore")

# Global variables
# TODO: Create a flag to let the user put a custom path

csv_files = []
for file in glob.glob(os.path.join(folder_path_compliance, "*.csv")):
    try:
        with open(
            file, "r", newline="", encoding=encoding_format, errors=error_action
        ) as csvfile:
            reader = csv.reader(csvfile)
            num_rows = sum(1 for row in reader)
            if num_rows > 1:
                csv_files.append(file)
    except UnicodeDecodeError:
        logger.error(f"Error decoding file: {file}")


def load_csv_files(csv_files):
    # Load CSV files into a single pandas DataFrame.
    dfs = []
    results = []
    for file in csv_files:
        df = pd.read_csv(file, sep=";", on_bad_lines="skip", encoding=encoding_format)
        if "CHECKID" in df.columns:
            dfs.append(df)
            result = file
            result = result.split("/")[-1]
            result = re.sub(r"^.*?_", "", result)
            result = result.replace(".csv", "")
            result = result.upper()
            if "AWS" in result:
                if "AWS_" in result:
                    result = result.replace("_AWS", "")
                else:
                    result = result.replace("_AWS", " - AWS")
            if "GCP" in result:
                result = result.replace("_GCP", " - GCP")
            if "AZURE" in result:
                result = result.replace("_AZURE", " - AZURE")
            if "KUBERNETES" in result:
                result = result.replace("_KUBERNETES", " - KUBERNETES")
            if "M65" in result:
                result = result.replace("_M65", " - M65")
            results.append(result)

    unique_results = set(results)
    results = list(unique_results)
    # Check if there is any CIS report in the list and divide it in level 1 and level 2
    new_results = []
    old_results = results.copy()
    for compliance_name in results:
        if "CIS_" in compliance_name:
            old_results.remove(compliance_name)
            new_results.append(compliance_name + " - Level_1")
            new_results.append(compliance_name + " - Level_2")

    results = old_results + new_results
    results.sort()
    # Handle the case where there are no CSV files
    try:
        data = pd.concat(dfs, ignore_index=True)
    except ValueError:
        data = None
    return data, results


data, results = load_csv_files(csv_files)

if data is None:
    dash.register_page(__name__)
    layout = html.Div(
        [
            html.Div(
                [
                    html.H5(
                        "No data found, check if the CSV files are in the correct folder.",
                        className="card-title",
                        style={"text-align": "left"},
                    )
                ],
                style={
                    "width": "99%",
                    "margin-right": "0.8%",
                    "margin-bottom": "10px",
                },
            )
        ]
    )
else:

    data["ASSESSMENTDATE"] = pd.to_datetime(data["ASSESSMENTDATE"])
    data["ASSESSMENT_TIME"] = data["ASSESSMENTDATE"].dt.strftime("%Y-%m-%d %H:%M:%S")

    data_values = data["ASSESSMENT_TIME"].unique()
    data_values.sort()
    data_values = data_values[::-1]
    aux = []
    for value in data_values:
        if value.split(" ")[0] not in [aux[i].split(" ")[0] for i in range(len(aux))]:
            aux.append(value)
    data_values = aux

    data = data[data["ASSESSMENT_TIME"].isin(data_values)]
    data["ASSESSMENT_TIME"] = data["ASSESSMENT_TIME"].apply(lambda x: x.split(" ")[0])

    # Select Compliance - Dropdown

    compliance_dropdown = create_compliance_dropdown(results)

    # Select Account - Dropdown

    select_account_dropdown_list = ["All"]
    # Append to the list the unique values of the columns ACCOUNTID, PROJECTID and SUBSCRIPTIONID if they exist
    if "ACCOUNTID" in data.columns:
        data["ACCOUNTID"] = data["ACCOUNTID"].astype(str)
        select_account_dropdown_list = select_account_dropdown_list + list(
            data["ACCOUNTID"].unique()
        )
    if "PROJECTID" in data.columns:
        select_account_dropdown_list = select_account_dropdown_list + list(
            data["PROJECTID"].unique()
        )
    if "SUBSCRIPTIONID" in data.columns:
        select_account_dropdown_list = select_account_dropdown_list + list(
            data["SUBSCRIPTIONID"].unique()
        )
    if "SUBSCRIPTION" in data.columns:
        select_account_dropdown_list = select_account_dropdown_list + list(
            data["SUBSCRIPTION"].unique()
        )

    list_items = []
    for item in select_account_dropdown_list:
        if item.__class__.__name__ == "str" and "nan" not in item:
            list_items.append(item)

    account_dropdown = create_account_dropdown_compliance(list_items)

    # Select Region - Dropdown

    select_region_dropdown_list = ["All"]
    # Append to the list the unique values of the column REGION or LOCATION if it exists
    if "REGION" in data.columns:
        # Handle the case where the column REGION is empty
        data["REGION"] = data["REGION"].fillna("-")
        select_region_dropdown_list = select_region_dropdown_list + list(
            data["REGION"].unique()
        )
    if "LOCATION" in data.columns:
        # Handle the case where the column LOCATION is empty
        data["LOCATION"] = data["LOCATION"].fillna("-")
        select_region_dropdown_list = select_region_dropdown_list + list(
            data["LOCATION"].unique()
        )

    # Clear the list from None and NaN values
    list_items = []
    for item in select_region_dropdown_list:
        if item.__class__.__name__ == "str":
            list_items.append(item)

    region_dropdown = create_region_dropdown_compliance(list_items)

    # Select Date - Dropdown

    date_dropdown = create_date_dropdown_compliance(
        list(data["ASSESSMENT_TIME"].unique())
    )

    dash.register_page(__name__)

    layout = create_layout_compliance(
        account_dropdown, date_dropdown, region_dropdown, compliance_dropdown
    )


@callback(
    [
        Output("output", "children"),
        Output("overall_status_result_graph", "children"),
        Output("security_level_graph", "children"),
        Output("cloud-account-filter-compliance", "value"),
        Output("cloud-account-filter-compliance", "options"),
        Output("region-filter-compliance", "value"),
        Output("region-filter-compliance", "options"),
        Output("date-filter-analytics", "value"),
        Output("date-filter-analytics", "options"),
    ],
    Input("report-compliance-filter", "value"),
    Input("cloud-account-filter-compliance", "value"),
    Input("region-filter-compliance", "value"),
    Input("date-filter-analytics", "value"),
)
def display_data(
    analytics_input, account_filter, region_filter_analytics, date_filter_analytics
):

    current_compliance = analytics_input
    analytics_input = analytics_input.replace(" - ", "_")
    analytics_input = analytics_input.lower()

    # Check if the compliance selected is the level 1 or level 2 of the CIS
    is_level_1 = "level_1" in analytics_input
    analytics_input = analytics_input.replace("_level_1", "").replace("_level_2", "")

    # Filter the data based on the compliance selected
    files = [file for file in csv_files if analytics_input in file]

    def load_csv_files(files):
        """Load CSV files into a single pandas DataFrame."""
        dfs = []
        for file in files:
            df = pd.read_csv(
                file, sep=";", on_bad_lines="skip", encoding=encoding_format, dtype=str
            )
            df = df.astype(str).fillna("nan")
            df.columns = df.columns.astype(str)
            dfs.append(df)
        return pd.concat(dfs, ignore_index=True)

    data = load_csv_files(files)

    # Rename the column LOCATION to REGION for GCP or Azure
    if "gcp" in analytics_input or "azure" in analytics_input:
        data = data.rename(columns={"LOCATION": "REGION"})

    # Add the column ACCOUNTID to the data if the provider is kubernetes
    if "kubernetes" in analytics_input:
        data.rename(columns={"CONTEXT": "ACCOUNTID"}, inplace=True)
        data.rename(columns={"NAMESPACE": "REGION"}, inplace=True)
        if "REQUIREMENTS_ATTRIBUTES_PROFILE" in data.columns:
            data["REQUIREMENTS_ATTRIBUTES_PROFILE"] = data[
                "REQUIREMENTS_ATTRIBUTES_PROFILE"
            ].apply(lambda x: x.split(" - ")[0])

    # Add the column ACCOUNTID to the data if the provider is m65
    if "m365" in analytics_input:
        data.rename(columns={"TENANTID": "ACCOUNTID"}, inplace=True)
        data.rename(columns={"LOCATION": "REGION"}, inplace=True)
        if "REQUIREMENTS_ATTRIBUTES_PROFILE" in data.columns:
            data["REQUIREMENTS_ATTRIBUTES_PROFILE"] = data[
                "REQUIREMENTS_ATTRIBUTES_PROFILE"
            ].apply(lambda x: x.split(" - ")[0])
    # Filter the chosen level of the CIS
    if is_level_1:
        data = data[data["REQUIREMENTS_ATTRIBUTES_PROFILE"] == "Level 1"]

    # Rename the column PROJECTID to ACCOUNTID for GCP
    if data.columns.str.contains("PROJECTID").any():
        data.rename(columns={"PROJECTID": "ACCOUNTID"}, inplace=True)
        data["REGION"] = "-"
    # Rename the column SUBSCRIPTIONID to ACCOUNTID for Azure
    if (
        data.columns.str.contains("SUBSCRIPTIONID").any()
        and not data.columns.str.contains("ACCOUNTID").any()
    ):
        data.rename(columns={"SUBSCRIPTIONID": "ACCOUNTID"}, inplace=True)
        data["REGION"] = "-"
    # Handle v3 azure cis compliance
    if (
        data.columns.str.contains("SUBSCRIPTION").any()
        and not data.columns.str.contains("ACCOUNTID").any()
    ):
        data.rename(columns={"SUBSCRIPTION": "ACCOUNTID"}, inplace=True)
        data["REGION"] = "-"

    # Filter ACCOUNT
    if account_filter == ["All"]:
        updated_cloud_account_values = data["ACCOUNTID"].unique()

    elif "All" in account_filter and len(account_filter) > 1:
        # Remove 'All' from the list
        account_filter.remove("All")
        updated_cloud_account_values = account_filter
    elif len(account_filter) == 0:
        updated_cloud_account_values = data["ACCOUNTID"].unique()
        account_filter = ["All"]
    else:
        updated_cloud_account_values = account_filter

    data = data[data["ACCOUNTID"].isin(updated_cloud_account_values)]

    account_filter_options = list(data["ACCOUNTID"].unique())
    account_filter_options = account_filter_options + ["All"]
    account_filter_options = [
        item
        for item in account_filter_options
        if isinstance(item, str) and item.lower() != "nan"
    ]

    # Filter REGION
    if region_filter_analytics == ["All"]:
        updated_region_account_values = data["REGION"].unique()
    elif "All" in region_filter_analytics and len(region_filter_analytics) > 1:
        # Remove 'All' from the list
        region_filter_analytics.remove("All")
        updated_region_account_values = region_filter_analytics
    elif len(region_filter_analytics) == 0:
        updated_region_account_values = data["REGION"].unique()
        region_filter_analytics = ["All"]
    else:
        updated_region_account_values = region_filter_analytics

    data = data[data["REGION"].isin(updated_region_account_values)]

    region_filter_options = list(data["REGION"].unique())
    region_filter_options = region_filter_options + ["All"]
    for item in region_filter_options:
        if item == "nan" or item.__class__.__name__ != "str":
            region_filter_options.remove(item)

    # Convert ASSESSMENTDATE to datetime
    data["ASSESSMENTDATE"] = pd.to_datetime(data["ASSESSMENTDATE"], errors="coerce")
    data["ASSESSMENTDAY"] = data["ASSESSMENTDATE"].dt.date

    # Find the latest timestamp per account per day
    latest_per_account_day = data.groupby(["ACCOUNTID", "ASSESSMENTDAY"])[
        "ASSESSMENTDATE"
    ].transform("max")

    # Keep only rows with the latest timestamp for each account and day
    data = data[data["ASSESSMENTDATE"] == latest_per_account_day]

    # Prepare the date filter options (unique days, as strings)
    options_date = sorted(data["ASSESSMENTDAY"].astype(str).unique(), reverse=True)

    # Filter by selected date (as string)
    if date_filter_analytics in options_date:
        data = data[data["ASSESSMENTDAY"].astype(str) == date_filter_analytics]
    else:
        date_filter_analytics = options_date[0]
        data = data[data["ASSESSMENTDAY"].astype(str) == date_filter_analytics]

    if data.empty:
        fig = px.pie()
        pie_1 = dcc.Graph(
            figure=fig,
            config={"displayModeBar": False},
            style={"height": "250px", "width": "250px", "right": "0px"},
        )

        return [
            html.Div(
                [
                    html.H5(
                        "No data found for this compliance",
                        className="card-title",
                        style={"text-align": "left"},
                    )
                ],
                style={
                    "width": "99%",
                    "margin-right": "0.8%",
                    "margin-bottom": "10px",
                },
            )
        ]
    else:
        # Check cases where the compliance start with AWS_
        if "aws_" in analytics_input:
            analytics_input = analytics_input + "_aws"
        try:
            current = analytics_input.replace(".", "_")
            compliance_module = importlib.import_module(
                f"dashboard.compliance.{current}"
            )
            data = data.drop_duplicates(
                subset=["CHECKID", "STATUS", "MUTED", "RESOURCEID", "STATUSEXTENDED"]
            )

            if "threatscore" in analytics_input:
                data = get_threatscore_mean_by_pillar(data)

            table = compliance_module.get_table(data)
        except ModuleNotFoundError:
            table = html.Div(
                [
                    html.H5(
                        "No data found for this compliance",
                        className="card-title",
                        style={"text-align": "left", "color": "black"},
                    )
                ],
                style={
                    "width": "99%",
                    "margin-right": "0.8%",
                    "margin-bottom": "10px",
                },
            )

        df = data.copy()
        # Remove Muted rows
        if "MUTED" in df.columns:
            df = df[df["MUTED"] == "False"]
        df = df.groupby(["STATUS"]).size().reset_index(name="counts")
        df = df.sort_values(by=["counts"], ascending=False)

        # Pie 1
        pie_1 = get_pie(df)

        # Get the pie2 depending on the compliance
        df = data.copy()

        current_filter = ""

        if "pci" in analytics_input:
            pie_2 = get_bar_graph(df, "REQUIREMENTS_ID")
            current_filter = "req_id"
        elif "threatscore" in analytics_input:
            pie_2 = get_table_prowler_threatscore(df)
            current_filter = "threatscore"
        elif (
            "REQUIREMENTS_ATTRIBUTES_SECTION" in df.columns
            and not df["REQUIREMENTS_ATTRIBUTES_SECTION"].isnull().values.any()
        ):
            pie_2 = get_bar_graph(df, "REQUIREMENTS_ATTRIBUTES_SECTION")
            current_filter = "sections"
        elif (
            "REQUIREMENTS_ATTRIBUTES_CATEGORIA" in df.columns
            and not df["REQUIREMENTS_ATTRIBUTES_CATEGORIA"].isnull().values.any()
        ):
            pie_2 = get_bar_graph(df, "REQUIREMENTS_ATTRIBUTES_CATEGORIA")
            current_filter = "categorias"
        elif (
            "REQUIREMENTS_ATTRIBUTES_CATEGORY" in df.columns
            and not df["REQUIREMENTS_ATTRIBUTES_CATEGORY"].isnull().values.any()
        ):
            pie_2 = get_bar_graph(df, "REQUIREMENTS_ATTRIBUTES_CATEGORY")
            current_filter = "categories"
        elif (
            "REQUIREMENTS_ATTRIBUTES_SERVICE" in df.columns
            and not df["REQUIREMENTS_ATTRIBUTES_SERVICE"].isnull().values.any()
        ):
            pie_2 = get_bar_graph(df, "REQUIREMENTS_ATTRIBUTES_SERVICE")
            current_filter = "services"
        elif (
            "REQUIREMENTS_ID" in df.columns
            and not df["REQUIREMENTS_ID"].isnull().values.any()
        ):
            pie_2 = get_bar_graph(df, "REQUIREMENTS_ID")
            current_filter = "techniques"
        else:
            fig = px.pie()
            fig.update_layout(
                margin=dict(l=0, r=0, t=0, b=0),
                autosize=True,
                showlegend=False,
                paper_bgcolor="#303030",
            )
            pie_2 = dcc.Graph(
                figure=fig,
                config={"displayModeBar": False},
                style={"height": "250px", "width": "250px", "right": "0px"},
            )
            current_filter = "none"

    # Analytics table

    if not analytics_input:
        analytics_input = ""

    table_output = get_table(current_compliance, table)

    overall_status_result_graph = get_graph(pie_1, "Overall Status Result")

    security_level_graph = get_graph(
        pie_2, f"Top 5 failed {current_filter} by requirements"
    )

    if "threatscore" in analytics_input:
        security_level_graph = get_graph(
            pie_2,
            "Pillar Score by requirements (1 = Lowest Risk, 5 = Highest Risk)",
            margin_top=0,
        )

    return (
        table_output,
        overall_status_result_graph,
        security_level_graph,
        account_filter,
        account_filter_options,
        region_filter_analytics,
        region_filter_options,
        date_filter_analytics,
        options_date,
    )


def get_graph(pie, title, margin_top=7):
    return [
        html.Span(
            title,
            className="text-center text-prowler-stone-900 uppercase text-xs font-bold",
        ),
        html.Div(
            [pie],
            className="",
            style={
                "display": "flex",
                "justify-content": "center",
                "align-items": "center",
                "margin-top": f"{margin_top}%",
            },
        ),
    ]


def get_bar_graph(df, column_name):
    df = df[df["STATUS"] == "FAIL"]
    df = df.groupby([column_name, "STATUS"]).size().reset_index(name="counts")
    df = df.sort_values(by=["counts"], ascending=True)
    # take the top 5
    df = df.tail(5)

    colums = df[column_name].unique()

    # Cut the text if it is too long
    for i in range(len(colums)):
        if len(colums[i]) > 43:
            colums[i] = colums[i][:43] + "..."

    fig = px.bar(
        df,
        x="counts",
        y=colums,
        color="STATUS",
        color_discrete_map={"FAIL": fail_color},
        orientation="h",
    )

    fig.update_layout(
        margin=dict(l=0, r=0, t=0, b=0),
        autosize=True,
        showlegend=False,
        xaxis_title=None,
        yaxis_title=None,
        font=dict(size=14, color="#292524"),
        hoverlabel=dict(font_size=12),
        paper_bgcolor="#FFF",
    )

    return dcc.Graph(
        figure=fig,
        config={"displayModeBar": False},
        style={"height": "20rem", "width": "40rem"},
    )


def get_pie(df):
    # Define custom colors
    color_mapping = {
        "FAIL": fail_color,
        "PASS": pass_color,
        "INFO": info_color,
        "WARN": "#260000",
        "MANUAL": manual_color,
    }

    # Use the color_discrete_map parameter to map categories to custom colors
    fig = px.pie(
        df,
        names="STATUS",
        values="counts",
        hole=0.7,
        color="STATUS",
        color_discrete_map=color_mapping,
    )
    fig.update_traces(
        hovertemplate=None,
        textposition="outside",
        textinfo="percent+label",
        rotation=50,
    )

    fig.update_layout(
        margin=dict(l=0, r=0, t=0, b=0),
        autosize=True,
        showlegend=False,
        font=dict(size=14, color="#292524"),
        hoverlabel=dict(font_size=12),
        paper_bgcolor="#FFF",
    )

    pie = dcc.Graph(
        figure=fig,
        config={"displayModeBar": False},
        style={"height": "20rem", "width": "20rem"},
    )

    return pie


def get_table(current_compliance, table):
    return [
        html.Div(
            [
                html.H5(
                    f"{current_compliance}",
                    className="text-prowler-stone-900 text-md font-bold uppercase mb-4",
                ),
                table,
            ],
            className="relative flex flex-col bg-white shadow-provider rounded-xl px-4 py-3 flex-wrap w-full",
        ),
    ]


def get_threatscore_mean_by_pillar(df):
    score_per_pillar = {}
    max_score_per_pillar = {}

    for _, row in df.iterrows():
        pillar = (
            row["REQUIREMENTS_ATTRIBUTES_SECTION"].split(" - ")[0]
            if isinstance(row["REQUIREMENTS_ATTRIBUTES_SECTION"], str)
            else "Unknown"
        )

        if pillar not in score_per_pillar:
            score_per_pillar[pillar] = 0
            max_score_per_pillar[pillar] = 0

        level_of_risk = pd.to_numeric(
            row["REQUIREMENTS_ATTRIBUTES_LEVELOFRISK"], errors="coerce"
        )
        level_of_risk = 1 if pd.isna(level_of_risk) else level_of_risk

        weight = 1
        if "REQUIREMENTS_ATTRIBUTES_WEIGHT" in row and not pd.isna(
            row["REQUIREMENTS_ATTRIBUTES_WEIGHT"]
        ):
            weight = pd.to_numeric(
                row["REQUIREMENTS_ATTRIBUTES_WEIGHT"], errors="coerce"
            )
            weight = 1 if pd.isna(weight) else weight

        max_score_per_pillar[pillar] += level_of_risk * weight

        if row["STATUS"] == "PASS":
            score_per_pillar[pillar] += level_of_risk * weight

    output = []
    for pillar in max_score_per_pillar:
        risk_score = 0
        if max_score_per_pillar[pillar] > 0:
            risk_score = (score_per_pillar[pillar] / max_score_per_pillar[pillar]) * 100

        output.append(f"{pillar} - [{risk_score:.1f}%]")

    for value in output:
        base_pillar = value.split(" - ")[0]
        if base_pillar in df["REQUIREMENTS_ATTRIBUTES_SECTION"].values:
            df.loc[
                df["REQUIREMENTS_ATTRIBUTES_SECTION"] == base_pillar,
                "REQUIREMENTS_ATTRIBUTES_SECTION",
            ] = value

    return df


def get_table_prowler_threatscore(df):
    score_per_pillar = {}
    max_score_per_pillar = {}
    pillars = {}

    df_copy = df.copy()

    for _, row in df_copy.iterrows():
        pillar = (
            row["REQUIREMENTS_ATTRIBUTES_SECTION"].split(" - ")[0]
            if isinstance(row["REQUIREMENTS_ATTRIBUTES_SECTION"], str)
            else "Unknown"
        )

        if pillar not in pillars:
            pillars[pillar] = {"FAIL": 0, "PASS": 0, "MUTED": 0}
            score_per_pillar[pillar] = 0
            max_score_per_pillar[pillar] = 0

        level_of_risk = pd.to_numeric(
            row["REQUIREMENTS_ATTRIBUTES_LEVELOFRISK"], errors="coerce"
        )
        level_of_risk = 1 if pd.isna(level_of_risk) else level_of_risk

        weight = 1
        if "REQUIREMENTS_ATTRIBUTES_WEIGHT" in row and not pd.isna(
            row["REQUIREMENTS_ATTRIBUTES_WEIGHT"]
        ):
            weight = pd.to_numeric(
                row["REQUIREMENTS_ATTRIBUTES_WEIGHT"], errors="coerce"
            )
            weight = 1 if pd.isna(weight) else weight

        max_score_per_pillar[pillar] += level_of_risk * weight

        if row["STATUS"] == "PASS":
            pillars[pillar]["PASS"] += 1
            score_per_pillar[pillar] += level_of_risk * weight
        elif row["STATUS"] == "FAIL":
            pillars[pillar]["FAIL"] += 1

        if "MUTED" in row and row["MUTED"] == "True":
            pillars[pillar]["MUTED"] += 1

    result_df = []

    for pillar in pillars.keys():
        risk_score = 0
        if max_score_per_pillar[pillar] > 0:
            risk_score = (score_per_pillar[pillar] / max_score_per_pillar[pillar]) * 100

        result_df.append({"Pillar": pillar, "Score": risk_score})

    score_df = pd.DataFrame(result_df)

    score_df = score_df.sort_values("Score", ascending=True)

    fig = px.bar(
        score_df,
        x="Pillar",
        y="Score",
        color="Score",
        color_continuous_scale=[
            "#e77676",
            "#f4d44d",
            "#45cc6e",
        ],
        labels={"Score": "Risk Score (%)", "Pillar": "Section"},
        height=400,
        text="Score",
    )

    fig.update_traces(texttemplate="%{text:.1f}%", textposition="outside")

    fig.update_layout(
        xaxis_title="Pillar",
        yaxis_title="Risk Score (%)",
        margin=dict(l=20, r=20, t=30, b=20),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        coloraxis_colorbar=dict(title="Risk %"),
        yaxis=dict(range=[0, 110]),
    )

    return dcc.Graph(
        figure=fig,
        style={"height": "25rem", "width": "40rem"},
    )
