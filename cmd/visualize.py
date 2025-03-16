import os
import sys
import logging
from dotenv import load_dotenv
from rich.logging import RichHandler
from rich.console import Console
from langchain_openai import OpenAIEmbeddings
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.manifold import TSNE

# autopep8: off # Add parent directory to path to allow absolute imports
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)

from db import mongoatlas
# autopep8: on


# Setup logging
load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[RichHandler(console=Console(width=200))]
)
logger = logging.getLogger(__name__)


def main():
    # Initialize services
    embedding_model = "text-embedding-3-large"
    mongodb_conn_sr = os.environ.get("MONGODB_CONNECTION_STRING")

    # Initialize MongoDB
    embeddings = OpenAIEmbeddings(model=embedding_model)
    mongodb_helper = mongoatlas.MongoDBHelper(
        connection_str=mongodb_conn_sr,
        db_name="tipitaka-viet-db",
        vector_store_name="facts__text-embedding-3-large",
        secondary_vector_store_name="secondary-facts__text-embedding-3-large",
        vector_store_index=embedding_model,
    )
    vector_store = mongodb_helper.create_secondary_vector_store(
        embeddings, dimensions=3072, should_skip_creating_index=True
    )

    collection = vector_store.collection

    # 2. Fetch embedded data
    data = list(collection.find({}, {"_id": 0, "embedding": 1, "source": 1}).limit(1000))

    # 3. Convert to DataFrame
    df = pd.DataFrame(data)
    df["embedding"] = df["embedding"].apply(lambda x: np.array(x))  # Convert to NumPy arrays
    matrix = np.vstack(df["embedding"].values)  # Convert list of arrays into a matrix

    # 4. Apply t-SNE for dimensionality reduction
    tsne = TSNE(n_components=2, perplexity=15, random_state=42, init='random', learning_rate=200)
    vis_dims = tsne.fit_transform(matrix)

    # 5. Prepare for visualization
    x = [x for x, y in vis_dims]
    y = [y for x, y in vis_dims]

    # Assign colors based on "source"
    unique_sources = df["source"].unique()
    color_map = {source: i for i, source in enumerate(unique_sources)}
    color_indices = df["source"].map(color_map).astype(int)

    # 6. Visualization
    plt.figure(figsize=(10, 6))
    scatter = plt.scatter(x, y, c=color_indices, cmap="viridis", alpha=0.6, edgecolors="k")
    plt.title("Text Embeddings Visualized using t-SNE")
    plt.xlabel("t-SNE Dimension 1")
    plt.ylabel("t-SNE Dimension 2")
    plt.colorbar(label="Source Index")
    plt.show()


if __name__ == "__main__":
    main()
