from langchain_core.output_parsers import StrOutputParser, JsonOutputParser



def create_str_chain(prompt, model, ):

    # Create the generate chain
    generate_chain = prompt | model | StrOutputParser()

    return generate_chain


def create_json_chain(prompt, model,):
    """
    Creates a standard generate chain for all application.

    Args:
        llm (LLM): The language model to use for generating responses.

    Returns:
        returns a string response.
    """

    # Create the generate chain
    generate_chain = prompt | model | JsonOutputParser()

    return generate_chain


def create_structured_chain(prompt, model, structured_data):
    """
    Creates a standard generate chain for all application.

    Args:
        llm (LLM): The language model to use for generating responses.

    Returns:
        returns a string response.
    """

    structured_llm = model.with_structured_output(structured_data)
    generate_chain = prompt | structured_llm

    return generate_chain
