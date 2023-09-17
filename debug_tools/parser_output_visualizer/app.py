import os
from collections import Counter
from dataclasses import dataclass

import sec_parser as sp
import streamlit as st
import streamlit_antd_components as sac
from _sec_parser_library_facade import (
    download_html_from_ticker,
    download_html_from_url,
    get_semantic_elements,
    get_semantic_tree,
)
from _utils.misc import get_pretty_class_name, remove_ix_tags
from _utils.streamlit_ import (
    st_expander_allow_nested,
    st_hide_streamlit_element,
    st_multiselect_allow_long_titles,
    st_radio,
)
from _utils.streamlit_ import NotHashed
from dotenv import load_dotenv
from sec_parser.data_sources.secapio_data_retriever import (
    SecapioApiKeyInvalidError,
    SecapioApiKeyNotSetError,
    SecapioDataRetriever,
)
from sec_parser.semantic_elements.semantic_elements import IrrelevantElement

load_dotenv()


def streamlit_app(
    *,
    run_page_config=True,
    extra_steps: list["ProcessStep"] | None = None,
) -> "StreamlitAppReturn":
    # Returned values
    html = None
    elements = None
    tree = None
    selected_step = None

    if run_page_config:
        st.set_page_config(
            page_icon="🏦",
            page_title="SEC Parser Output Visualizer",
            layout="centered",
            initial_sidebar_state="expanded",
        )
    st_expander_allow_nested()
    st_hide_streamlit_element("class", "stDeployButton")
    st_multiselect_allow_long_titles()

    secapio_api_key_name = SecapioDataRetriever.API_KEY_ENV_VAR_NAME
    secapio_api_key = os.environ.get(secapio_api_key_name, "")
    secapio_api_key = st.session_state.get(secapio_api_key_name, "")
    if secapio_api_key_name not in os.environ:
        with st.sidebar.expander("API Key", expanded=not bool(secapio_api_key)):
            st.write(
                "The API key is required for parsing files that haven't been pre-downloaded."
                "You can obtain a free one from [sec-api.io](https://sec-api.io)."
            )
            secapio_api_key = st.text_input(
                type="password",
                label="Enter your API key:",
                value=secapio_api_key,
            )
            with st.expander("Why do I need an API key?"):
                st.write(
                    "We're currently using *sec-api.io* to handle the removal of the"
                    "title 10-Q page and to download 10-Q Section HTML files. In the"
                    "future, we aim to download these HTML files directly from the"
                    "SEC EDGAR. For now, you can get a free API key from"
                    "[sec-api.io](https://sec-api.io) and input it below."
                )
            st.session_state[secapio_api_key_name] = secapio_api_key
            msg = (
                "**Note:** Key will be deleted upon page refresh. We suggest"
                f"setting the `{secapio_api_key_name}` environment variable, possibly"
                "by creating an `.env` file at the root of the project. This method"
                "allows you to utilize the API key without the need for manual"
                "entry each time."
            )
            st.info(msg)

    with st.sidebar:
        st.write("# Select Report")
        data_source_options = [
            "Select Ticker to Find Latest",
            "Enter Ticker to Find Latest",
            "Enter SEC EDGAR URL",
        ]
        select_ticker, find_ticker, url = st_radio(
            "Select 10-Q Report Data Source", data_source_options
        )
        ticker, url = None, None
        if select_ticker:
            ticker = st.selectbox(
                label="Select Ticker",
                options=["AAPL", "GOOG"],
            )
        elif find_ticker:
            ticker = st.text_input(
                label="Enter Ticker",
                value="AAPL",
                placeholder="AAPL",
            )
            if not ticker:
                st.stop()
        else:
            url = st.text_input(
                label="Enter URL",
                value="https://www.sec.gov/Archives/edgar/data/320193/000032019323000077/aapl-20230701.htm",
            )

        section_1_2, all_sections = st_radio(
            "Select 10-Q Sections", ["Only MD&A", "All Sections"], horizontal=True
        )
        if section_1_2:
            sections = ["part1item2"]
        else:
            sections = None

    try:
        if ticker:
            html = download_html_from_ticker(
                NotHashed(secapio_api_key), doc="10-Q", ticker=ticker, sections=sections
            )
        else:
            html = download_html_from_url(
                NotHashed(secapio_api_key), doc="10-Q", url=url, sections=sections
            )
    except SecapioApiKeyNotSetError:
        st.error("**Error**: API key not set. Please provide a valid API key.")
        st.stop()
    except SecapioApiKeyInvalidError:
        st.error("**Error**: Invalid API key. Please check your API key and try again.")
        st.stop()

    process_steps = [
        ProcessStep(
            title="Original",
            caption="From SEC EDGAR",
        ),
        ProcessStep(
            title="Parsed",
            caption="Semantic Elements",
        ),
        ProcessStep(
            title="Structured",
            caption="Semantic Tree",
        ),
        *(extra_steps or []),
    ]
    selected_step = 1 + sac.steps(
        [
            sac.StepsItem(
                title=k.title,
                description=k.caption,
            )
            for k in process_steps
        ],
        index=2,
        format_func=None,
        placement="horizontal",
        size="default",
        direction="horizontal",
        type="default",  # default, navigation
        dot=False,
        return_index=True,
    )

    if selected_step == 1:
        st.markdown(remove_ix_tags(html), unsafe_allow_html=True)

    if selected_step >= 2:
        elements = get_semantic_elements(html)
        if selected_step <= 3:
            with st.sidebar:
                st.write("# Adjust View")
                left, right = st.columns(2)
                with left:
                    do_element_render_html = st.checkbox("Render HTML", value=True)
                with right:
                    do_expand_all = False
                    if selected_step == 2:
                        do_expand_all = st.checkbox("Expand All", value=False)

                counted_element_types = Counter(
                    element.__class__ for element in elements
                )
                format_cls = (
                    lambda cls: f'{counted_element_types[cls]}x {get_pretty_class_name(cls).replace("*","")}'
                )
                available_element_types = {
                    format_cls(cls): cls
                    for cls in sorted(
                        counted_element_types.keys(),
                        key=lambda x: counted_element_types[x],
                        reverse=True,
                    )
                }
                available_values = list(available_element_types.keys())
                preselected_types = [
                    format_cls(cls)
                    for cls in available_element_types.values()
                    if cls != IrrelevantElement
                ]
                selected_types = st.multiselect(
                    "Filter Element Types",
                    available_values,
                    preselected_types,
                )
                selected_types = [available_element_types[k] for k in selected_types]
                elements = [e for e in elements if e.__class__ in selected_types]

    if selected_step >= 3:
        tree = get_semantic_tree(elements)

    if selected_step == 3:
        with right:
            expand_depth = st.number_input("Expand Depth", min_value=0, value=0)

    def render_semantic_element(
        element: sp.BaseSemanticElement,
    ):
        if do_element_render_html:
            element_html = remove_ix_tags(str(element.html_tag._bs4))
            st.markdown(element_html, unsafe_allow_html=True)
        else:
            st.code(element.html_tag._bs4.prettify(), language="markup")

    def render_tree_node(tree_node: sp.TreeNode, _current_depth=0):
        element = tree_node.semantic_element
        expander_title = get_pretty_class_name(element.__class__, element)
        with st.expander(expander_title, expanded=expand_depth > _current_depth):
            render_semantic_element(element)
            for child in tree_node.children:
                render_tree_node(child, _current_depth=_current_depth + 1)

    if selected_step == 2:
        for element in elements:
            expander_title = get_pretty_class_name(element.__class__, element)
            with st.expander(expander_title, expanded=do_expand_all):
                render_semantic_element(element)

    if selected_step == 3:
        for root_node in tree.root_nodes:
            render_tree_node(root_node)

    return StreamlitAppReturn(
        html=html,
        elements=elements,
        tree=tree,
        selected_step=selected_step,
    )


@dataclass
class StreamlitAppReturn:
    html: str
    elements: list[sp.BaseSemanticElement]
    tree: sp.SemanticTree
    selected_step: int


@dataclass
class ProcessStep:
    title: str
    caption: str


if __name__ == "__main__":
    streamlit_app()

    # ai_step = ProcessStep(title="Value Added", caption="AI Applications")
    # r = streamlit_app(extra_steps=[ai_step])
    # if r.selected_step == 4:
    #     st.write("🚧 Work in progress...")
