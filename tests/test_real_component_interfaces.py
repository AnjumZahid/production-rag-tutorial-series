import importlib
import inspect
from types import ModuleType
from typing import Any


MODULES = {
    "PDF loader": (
        "backend.app.ingestion.loaders.pdf_loader"
    ),
    "PDF parser": (
        "backend.app.ingestion.parsers.pdf_parser"
    ),
    "Text cleaner": (
        "backend.app.ingestion.processors.text_cleaner"
    ),
    "Document chunker": (
        "backend.app.ingestion.processors.chunker"
    ),
    "Hugging Face embeddings": (
        "backend.app.embeddings.huggingface"
    ),
    "Embedding factory": (
        "backend.app.embeddings.factory"
    ),
    "Chroma vector store": (
        "backend.app.vectorstores.chroma_store"
    ),
    "Vector-store factory": (
        "backend.app.vectorstores.factory"
    ),
}


def safe_signature(value: Any) -> str:
    """Return a readable signature without failing the inspection test."""

    try:
        return str(inspect.signature(value))
    except (TypeError, ValueError):
        return "(signature unavailable)"


def print_class_details(
    class_name: str,
    class_object: type,
) -> None:
    """Print one class constructor and its public methods."""

    print(
        f"  Class: {class_name}"
        f"{safe_signature(class_object)}"
    )

    public_methods = []

    for method_name, method in inspect.getmembers(
        class_object,
        predicate=inspect.isfunction,
    ):
        if method_name.startswith("_"):
            continue

        public_methods.append(
            (
                method_name,
                safe_signature(method),
            )
        )

    if not public_methods:
        print("    Public methods: none detected")
        return

    print("    Public methods:")

    for method_name, signature in public_methods:
        print(
            f"      - {method_name}{signature}"
        )


def print_module_details(
    display_name: str,
    module_path: str,
    module: ModuleType,
) -> None:
    """Print classes and functions defined by one application module."""

    print("\n" + "=" * 78)
    print(display_name)
    print("Module:", module_path)
    print("=" * 78)

    found_member = False

    for member_name, member in inspect.getmembers(module):
        if member_name.startswith("_"):
            continue

        if (
            inspect.isclass(member)
            and member.__module__ == module.__name__
        ):
            found_member = True
            print_class_details(
                member_name,
                member,
            )

        elif (
            inspect.isfunction(member)
            and member.__module__ == module.__name__
        ):
            found_member = True
            print(
                f"  Function: "
                f"{member_name}{safe_signature(member)}"
            )

    if not found_member:
        print(
            "  No module-defined public classes "
            "or functions were detected."
        )


def main() -> None:
    print(
        "\n=== REAL COMPONENT INTERFACE AUDIT ==="
    )

    failed_imports: list[str] = []

    for display_name, module_path in MODULES.items():
        try:
            module = importlib.import_module(
                module_path
            )
        except Exception as exc:
            failed_imports.append(module_path)

            print("\n" + "=" * 78)
            print(display_name)
            print("Module:", module_path)
            print("=" * 78)
            print(
                "  Import failed:",
                type(exc).__name__,
                str(exc),
            )
            continue

        print_module_details(
            display_name=display_name,
            module_path=module_path,
            module=module,
        )

    if failed_imports:
        print("\nInterface audit finished with import failures:")

        for module_path in failed_imports:
            print("-", module_path)

        raise SystemExit(1)

    print(
        "\nAll real component modules imported successfully."
    )
    print(
        "Real component interface audit passed."
    )


if __name__ == "__main__":
    main()


# uv run python -m tests.test_real_component_interfaces