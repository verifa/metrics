"""simple office vibe data handler"""
import logging
import sys

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


class OfficeVibe:
    reports_file: str
    data: pd.DataFrame

    def __init__(self, reports_file: str = None) -> None:
        if reports_file is None:
            sys.exit("OfficeVibe reports file is missing")
        self.reports_file = reports_file

    def read_report(self) -> None:
        self.data = pd.read_csv(self.reports_file)
        self.data = self.data.sort_values(by="Date")

    def flip_data(self) -> None:
        self.data["Strongly Favorable"] = (
            self.data["Strongly Favorable"]
            + self.data["Favorable"]
            + self.data["Neutral"]
            + self.data["Unfavorable"]
            + self.data["Strongly unfavorable"]
        )
        self.data["Favorable"] = (
            self.data["Favorable"] + self.data["Neutral"] + self.data["Unfavorable"] + self.data["Strongly unfavorable"]
        )
        self.data["Neutral"] = self.data["Neutral"] + self.data["Unfavorable"] + self.data["Strongly unfavorable"]
        self.data["Unfavorable"] = self.data["Unfavorable"] + self.data["Strongly unfavorable"]

    def generate_figs(self):
        result = []

        for metric in self.data["Metric"].unique():
            for sub_metric in self.data[self.data["Metric"] == metric]["Sub Metric"].unique():
                questions = self.data[(self.data["Metric"] == metric) & (self.data["Sub Metric"] == sub_metric)][
                    "Question"
                ].unique()
                logging.debug(f"{metric}:{sub_metric} got {questions.size} questions")
                # how big need the sub-plot to be
                cols = 3
                rows = (cols - 1 + questions.size) // cols
                fig = make_subplots(rows=rows, cols=cols, subplot_titles=questions)
                i = 1
                for question in questions:
                    logging.debug(f"{i} - {metric}: {sub_metric}\n{question}")
                    data = self.data[
                        (self.data["Metric"] == metric)
                        & (self.data["Sub Metric"] == sub_metric)
                        & (self.data["Question"] == question)
                    ]
                    data = data.drop(["Metric", "Sub Metric", "Question"], axis="columns")
                    key_colors = {
                        "Strongly unfavorable": "red",
                        "Unfavorable": "darkred",
                        "Neutral": "darkgrey",
                        "Favorable": "darkgreen",
                        "Strongly Favorable": "green",
                    }
                    row = (cols - 1 + i) // cols
                    col = 1 + ((cols - 1 + i) % cols)
                    logging.debug(f"{i}: {row}:{col}")

                    for key in ["Strongly Favorable", "Favorable", "Neutral", "Unfavorable", "Strongly unfavorable"]:
                        if i == 1:
                            fig.append_trace(
                                go.Scatter(
                                    x=data["Date"],
                                    y=data[key],
                                    name=key,
                                    fill="tozeroy",
                                    line_color=key_colors[key],
                                    text=data["Sample"],
                                ),
                                row=1,
                                col=1,
                            )
                        else:
                            fig.append_trace(
                                go.Scatter(
                                    x=data["Date"],
                                    y=data[key],
                                    name="",
                                    fill="tozeroy",
                                    line_color=key_colors[key],
                                    showlegend=False,
                                    text=data["Sample"],
                                ),
                                row=row,
                                col=col,
                            )
                    i = i + 1
                fig.update_layout(
                    yaxis_range=[-5, 105],
                    height=400 * rows,
                    title=dict(
                        text=f"{metric}:{sub_metric}",
                        font=dict(family="Arial", size=20, color="#000000"),
                        x=0.45,
                        xanchor="center",
                        yanchor="top",
                    ),
                    font=dict(family="Arial"),
                )
                fig.update_annotations(font=dict(family="Arial", size=12))
                result.append(fig)
        return result
