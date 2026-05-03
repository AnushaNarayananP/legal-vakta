"""Command-line entry point for Legal Vakta."""

from src.agent.graph_builder import GraphBuilder
from src.config import Settings, get_llm
from src.retrieval.vectorstore import get_retriever, load_vectorstore


class LegalVaktaRAG:
    """Production-facing wrapper around the Legal Vakta graph."""

    def __init__(self):
        print("Initializing Legal Vakta...")
        vectorstore = load_vectorstore(Settings.vectorstore_dir)
        retriever = get_retriever(vectorstore, k=Settings.retriever_k)
        self.graph = GraphBuilder(retriever=retriever, llm=get_llm())
        self.graph.build()
        print("Legal Vakta is ready.\n")

    def ask(self, question: str) -> str:
        """Ask a question and print the answer with sources."""
        result = self.graph.run(question)
        print(f"\nAnswer:\n{result['answer']}\n")
        print("Sources:")
        for index, doc in enumerate(result["retrieved_docs"], start=1):
            metadata = doc.metadata
            print(
                f"{index}. {metadata.get('file_name', metadata.get('source'))} "
                f"| year={metadata.get('case_year')} | page={metadata.get('page')}"
            )
        return result["answer"]

    def interactive_mode(self):
        """Run Legal Vakta in a terminal chat loop."""
        print("Ask a criminal case research question. Type 'quit' to exit.\n")
        while True:
            question = input("Question: ").strip()
            if question.lower() in {"q", "quit", "exit"}:
                print("Goodbye.")
                break
            if question:
                self.ask(question)
                print("-" * 80)


def main():
    """Start the CLI assistant."""
    try:
        rag = LegalVaktaRAG()
    except FileNotFoundError as exc:
        print(exc)
        print("Run `python scripts/build_index.py` first.")
        return

    examples = [
        "What principles do Supreme Court criminal appeals discuss for appreciating evidence?",
        "Find cases discussing benefit of doubt in criminal appeals.",
    ]

    for question in examples:
        print(f"Example question: {question}")
        rag.ask(question)
        print("=" * 80)

    if input("Enter interactive mode? (y/n): ").strip().lower() == "y":
        rag.interactive_mode()


if __name__ == "__main__":
    main()
