from __future__ import annotations

from typing import TYPE_CHECKING

from sec_parser.processing_steps.abstract_elementwise_processing_step import (
    AbstractElementwiseTransformStep,
    ElementwiseProcessingContext,
)
from sec_parser.semantic_elements.semantic_elements import TableElement

if TYPE_CHECKING:
    from sec_parser.semantic_elements.abstract_semantic_element import (
        AbstractSemanticElement,
    )


class TableParsingStep(AbstractElementwiseTransformStep):
    """
    TableParsingStep class for transforming elements into TableElement instances.

    This step scans through a list of semantic elements and changes it,
    primarily by replacing suitable candidates with TableElement instances.
    """

    def _transform_element(
        self,
        element: AbstractSemanticElement,
        _: ElementwiseProcessingContext,
    ) -> AbstractSemanticElement:
        is_unary = element.html_tag.is_unary_tree()
        contains_table = element.html_tag.contains_tag("table", include_self=True)
        if is_unary and contains_table:
            return TableElement.convert_from(element)

        return element