from __future__ import annotations
from typing import Any, cast

from matplotlib import pyplot as plt, ticker, backend_bases
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.patches import FancyBboxPatch
from matplotlib.widgets import Slider
from mpl_interactions import zoom_factory

import json


class ScrollSlider(Slider):
    def __init__(self, maxis: Axes, ax: Axes, label, valmin, valmax, valinit):
        super().__init__(ax, label, valmin, valmax, valinit=valinit)
        self.on_changed(self._scroll)
        self.maxis = maxis
        self.fig = ax.get_figure()

    def _scroll(self, val):
        pos = val
        self.maxis.set_xlim(pos, pos + 100)
        self.fig.canvas.draw()  # type:ignore

    @classmethod
    def from_ax_fig(cls, fig: Figure, ax: Axes) -> ScrollSlider:
        slider_pos = fig.add_axes((0.13, 0.02, 0.757, 0.01))
        spos = ScrollSlider(ax, slider_pos, "", 0, 1000, valinit=0)
        return spos


class Render:
    def __init__(self, ax: Axes, simulation_log: str):

        self.axes = ax
        self.fig = cast(Figure, ax.get_figure())

        self.axes.set_ylim(1, 15)
        self.axes.set_xlim(-1, 1050)
        self.axes.xaxis.set_major_locator(ticker.MultipleLocator(base=10))
        self.axes.set_xlabel("Minutes from Start")

        # We'll store our FancyBboxPatch objects here.
        self.bars_list: list[FancyBboxPatch] = []

        with open(simulation_log, "r") as file:
            self.event_logs = json.load(file)

        for idx, task in enumerate(self.event_logs["logs"]):
            for event in task["task_events"]:
                if event["event_type"] == "job":
                    # Calculate the position and size of the bar.
                    start = event["event_start_timestamp"]
                    length = event["event_lenght"]
                    # Create a FancyBboxPatch with a rounded box style.
                    # The boxstyle "round,pad=0.02,rounding_size=5" gives rounded corners.
                    rect = FancyBboxPatch(
                        (start, (idx + 1) * 2),  # (x, y) position
                        length,  # width
                        0.5,  # height
                        boxstyle="round,pad=0.05,rounding_size=0.5",
                        # boxstyle="round,pad=0.02,rounding_size=5",
                        facecolor="tab:red",  # or cycle through colors as needed
                        edgecolor="black",
                        linewidth=1.5,
                        alpha=0.3,
                    )
                    self.axes.add_patch(rect)
                    self.bars_list.append(rect)

            for event in task["task_events"]:
                if event["event_type"] == "job":
                    # Second set of bars (if needed) with different styling.
                    start = event["event_start_timestamp"]
                    # Use event_end_timestamp if available, otherwise 0-length bar.
                    end = (
                        event.get("event_end_timestamp")
                        or event["event_start_timestamp"]
                    )
                    duration = end - start
                    rect = FancyBboxPatch(
                        (start, ((idx + 1) * 2) + 1),
                        duration,
                        0.5,
                        boxstyle="round,pad=.2",
                        # boxstyle="round,pad=0.02,rounding_size=5",
                        facecolor="tab:red",
                        edgecolor="black",
                        linewidth=0.8,
                        alpha=0.9,
                    )
                    self.axes.add_patch(rect)
                    self.bars_list.append(rect)

            for event in task["task_events"]:
                if event["event_type"] == "episode":
                    self.axes.scatter(
                        event["event_start_timestamp"],
                        (idx + 1) * 2 + 0.5,
                        marker="D",
                        color="blue",
                        s=37,
                        label="Episode" if idx == 0 else "",
                    )
            # Just process the first task for demonstration.
            break

        self.fig.canvas.mpl_connect("motion_notify_event", self.hover)

    def hover(self, event: backend_bases.Event) -> Any:
        for patch in self.bars_list:
            contains, _ = patch.contains(cast(backend_bases.MouseEvent, event))
            if contains:
                patch.set_alpha(0.8)
                patch.set_edgecolor("yellow")
                patch.set_linewidth(1.2)
            else:
                # Reset to original styling.
                # You might want to store the original values if they differ per patch.
                patch.set_alpha(0.3 if patch.get_facecolor()[0] == 1.0 else 0.9)
                patch.set_edgecolor("black")
                patch.set_linewidth(0.8)
        self.fig.canvas.draw_idle()


if __name__ == "__main__":

    fig, ax = plt.subplots()
    slider_pos = ScrollSlider.from_ax_fig(fig, ax)
    zoom_factory(ax)

    # Replace the path with your actual log file path.
    render = Render(ax, r"C:\Users\ansh1\codebase\iit-mba-941\test\logs.json")

    ax.set_xlim(0, 100)
    fig.canvas.draw_idle()
    plt.show()
