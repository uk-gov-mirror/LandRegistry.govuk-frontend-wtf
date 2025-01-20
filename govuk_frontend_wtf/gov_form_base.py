from typing import Any, Dict

from flask import render_template
from markupsafe import Markup
from wtforms import Field  # Import for type hinting

from govuk_frontend_wtf.main import merger


class GovFormBase(object):
    """Collection of helpers

    These are mixed into the WTForms classes which we are subclassing
    to provide extra functionality.

    Some of our subclasses then extend these base utilities for their
    specific use cases
    """

    template: str

    def __call__(self, field: Field, **kwargs: Any) -> Markup:
        return self.render(self.map_gov_params(field, **kwargs))

    def map_gov_params(self, field: Field, **kwargs: Any) -> Dict[str, Any]:
        """Map WTForms' html params to govuk macros

        Taking WTForms' output, we need to map it to a params dict
        which matches the structure that the govuk macros are expecting
        """
        params: Dict[str, Any] = {
            "id": kwargs["id"],
            "name": field.name,
            "label": {"text": field.label.text},
            "attributes": {},
            "hint": {"text": field.description} if field.description else None,
        }

        if "value" in kwargs:
            params["value"] = kwargs["value"]
            del kwargs["value"]

        # Not all form elements have a type so guard against it not existing
        if "type" in kwargs:
            params["type"] = kwargs["type"]
            del kwargs["type"]

        # Remove items that we've already used from the kwargs
        del kwargs["id"]
        if "items" in kwargs:
            del kwargs["items"]

        # Merge in any extra params passed in from the template layer
        if "params" in kwargs:
            params = self.merge_params(params, kwargs["params"])

            # And then remove it, to make sure it doesn't make it's way into the attributes below
            del kwargs["params"]

        # Map error messages
        if field.errors:
            params["errorMessage"] = {"text": field.errors[0]}

        # And then Merge any remaining attributes directly to the attributes param
        # This catches anything set in the more traditional WTForms manner
        # i.e. directly as kwargs passed into the field when it's rendered
        params["attributes"] = self.merge_params(params["attributes"], kwargs)

        # Map attributes such as required="True" to required="required"
        for key, value in params["attributes"].items():
            if value is True:
                params["attributes"][key] = key

        return params

    def merge_params(self, a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
        return merger.merge(a, b)

    def render(self, params: Dict[str, Any]) -> Markup:
        return Markup(render_template(self.template, params=params))


class GovIterableBase(GovFormBase):
    def __call__(self, field: Field, **kwargs: Any) -> Markup:
        kwargs.setdefault("id", field.id)

        if "required" not in kwargs and "required" in getattr(field, "flags", []):
            kwargs["required"] = True

        kwargs["items"] = []

        # This field is constructed as an iterable of subfields
        for subfield in field:
            item: Dict[str, Any] = {
                "text": subfield.label.text,
                "value": subfield._value(),
            }

            if getattr(subfield, "checked", subfield.data):
                item["checked"] = True

            kwargs["items"].append(item)

        return super().__call__(field, **kwargs)

    def map_gov_params(self, field: Field, **kwargs: Any) -> Dict[str, Any]:
        """Completely override the params mapping for this input type

        It bears little resemblance to that of a normal field
        because these fields are effectively collections of
        fields wrapped in an iterable
        """

        params: Dict[str, Any] = {
            "name": field.name,
            "items": kwargs["items"],
            "hint": {"text": field.description},
        }

        # Merge in any extra params passed in from the template layer
        if "params" in kwargs:
            # Merge items individually as otherwise the merge will append new ones
            if "items" in kwargs["params"]:
                for index, item in enumerate(kwargs["params"]["items"]):
                    params["items"][index] = self.merge_params(params["items"][index], item)  # Corrected this line

                del kwargs["params"]["items"]

            params = self.merge_params(params, kwargs["params"])

        if field.errors:
            params["errorMessage"] = {"text": field.errors[0]}

        return params
