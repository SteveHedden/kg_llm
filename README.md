# Integrating Knowneledge Graphs to Large Language Models

## Medium articles

* The notebook VectorVsKG.ipynb is the code associated with this tutorial: [How to Implement Graph RAG Using Knowledge Graphs and Vector Databases](https://towardsdatascience.com/how-to-implement-graph-rag-using-knowledge-graphs-and-vector-databases-60bb69a22759)

* The notebook SDKG.ipynb is the code associated with this tutorial: [Harnessing the Power of Knowledge Graphs: Enriching an LLM with Structured Data](https://medium.com/towards-data-science/harnessing-the-power-of-knowledge-graphs-enriching-an-llm-with-structured-data-997fabc62386?sk=552a8f07ad3a14a55c3b944c9bc484d2)

* The notebooks createTaxonomy.ipynb and tagMovies.ipynb, along with the moviesWithTags.csv are associated with this tutorial: [Unraveling Unstructured Movie Data](https://towardsdatascience.com/unraveling-unstructured-movie-data-04d5ff787600?source=friends_link&sk=567bca3ce60a8ccf71c0366a3ca07344)

## Project setup

### UV

[uv](https://docs.astral.sh/uv/) has been used to setup this python project.
The code describes the steps:

``` sh
uv venv .venv-py311 --python 3.11 --seed #seed is used to clone pip/wheel to this venv
source .venv-py311/bin/activate #it is necessary to activate the environment so the uv init command will create the VIRTUAL_ENVIRONMENT when the project is initialised
uv init 
export UV_PROJECT_ENVIRONMENT=$VIRTUAL_ENV #this command will enable uv add commands to store dependencies in the VIRTUAL_ENV set. This is not necessary if you use .venv
```

## Logging

### Articles

* [Medium - Logging: from basics to advanced practices](https://medium.com/@moraneus/python-logging-from-basics-to-advanced-practices-f8ca709059e1)

* [RealPython - Logging in Python](https://realpython.com/python-logging/)

* [structlog](https://www.structlog.org/en/stable/)