"""
    pint.delegates.formatter.base_formatter
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    Common class and function for all formatters.
    :copyright: 2022 by Pint Authors, see AUTHORS for more details.
    :license: BSD, see LICENSE for more details.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
import re
from functools import partial
from ...util import iterable
from ...compat import ndarray, np, Unpack
from ._helpers import (
    split_format,
    formatter,
    join_mu,
    join_unc,
    remove_custom_flags,
)

from ..._typing import Magnitude
from ._unit_handlers import BabelKwds, format_compound_unit, override_locale

if TYPE_CHECKING:
    from ...facets.plain import PlainQuantity, PlainUnit, MagnitudeT
    from ...facets.measurement import Measurement

_EXP_PATTERN = re.compile(r"([0-9]\.?[0-9]*)e(-?)\+?0*([0-9]+)")


class HTMLFormatter:
    def format_magnitude(
        self, magnitude: Magnitude, mspec: str = "", **babel_kwds: Unpack[BabelKwds]
    ) -> str:
        with override_locale(babel_kwds.get("locale", None)) as format_number:
            if hasattr(magnitude, "_repr_html_"):
                # If magnitude has an HTML repr, nest it within Pint's
                mstr = magnitude._repr_html_()  # type: ignore
                assert isinstance(mstr, str)
            else:
                if isinstance(magnitude, ndarray):
                    # Need to override for scalars, which are detected as iterable,
                    # and don't respond to printoptions.
                    if magnitude.ndim == 0:
                        mstr = format_number(magnitude, mspec)
                    else:
                        with np.printoptions(
                            formatter={"float_kind": partial(format_number, spec=mspec)}
                        ):
                            mstr = (
                                "<pre>" + format(magnitude).replace("\n", "") + "</pre>"
                            )
                elif not iterable(magnitude):
                    # Use plain text for scalars
                    mstr = format_number(magnitude, mspec)
                else:
                    # Use monospace font for other array-likes
                    mstr = (
                        "<pre>"
                        + format_number(magnitude, mspec).replace("\n", "<br>")
                        + "</pre>"
                    )

        m = _EXP_PATTERN.match(mstr)
        _exp_formatter = lambda s: f"<sup>{s}</sup>"

        if m:
            exp = int(m.group(2) + m.group(3))
            mstr = _EXP_PATTERN.sub(r"\1×10" + _exp_formatter(exp), mstr)

        return mstr

    def format_unit(
        self, unit: PlainUnit, uspec: str = "", **babel_kwds: Unpack[BabelKwds]
    ) -> str:
        units = format_compound_unit(unit, uspec, **babel_kwds)

        return formatter(
            units,
            as_ratio=True,
            single_denominator=True,
            product_fmt=r" ",
            division_fmt=r"{}/{}",
            power_fmt=r"{}<sup>{}</sup>",
            parentheses_fmt=r"({})",
        )

    def format_quantity(
        self,
        quantity: PlainQuantity[MagnitudeT],
        qspec: str = "",
        **babel_kwds: Unpack[BabelKwds],
    ) -> str:
        registry = quantity._REGISTRY

        mspec, uspec = split_format(
            qspec, registry.default_format, registry.separate_format_defaults
        )

        if iterable(quantity.magnitude):
            # Use HTML table instead of plain text template for array-likes
            joint_fstring = (
                "<table><tbody>"
                "<tr><th>Magnitude</th>"
                "<td style='text-align:left;'>{}</td></tr>"
                "<tr><th>Units</th><td style='text-align:left;'>{}</td></tr>"
                "</tbody></table>"
            )
        else:
            joint_fstring = "{} {}"

        return join_mu(
            joint_fstring,
            self.format_magnitude(quantity.magnitude, mspec, **babel_kwds),
            self.format_unit(quantity.units, uspec, **babel_kwds),
        )

    def format_uncertainty(
        self,
        uncertainty,
        unc_spec: str = "",
        **babel_kwds: Unpack[BabelKwds],
    ) -> str:
        unc_str = format(uncertainty, unc_spec).replace("+/-", " &plusmn; ")

        unc_str = re.sub(r"\)e\+0?(\d+)", r")×10<sup>\1</sup>", unc_str)
        unc_str = re.sub(r"\)e-0?(\d+)", r")×10<sup>-\1</sup>", unc_str)
        return unc_str

    def format_measurement(
        self,
        measurement: Measurement,
        meas_spec: str = "",
        **babel_kwds: Unpack[BabelKwds],
    ) -> str:
        registry = measurement._REGISTRY

        mspec, uspec = split_format(
            meas_spec, registry.default_format, registry.separate_format_defaults
        )

        unc_spec = remove_custom_flags(meas_spec)

        joint_fstring = "{} {}"

        return join_unc(
            joint_fstring,
            "(",
            ")",
            self.format_uncertainty(measurement.magnitude, unc_spec, **babel_kwds),
            self.format_unit(measurement.units, uspec, **babel_kwds),
        )