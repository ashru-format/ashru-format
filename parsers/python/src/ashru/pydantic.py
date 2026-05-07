from typing import TypeVar, Type, Generic, List, Any
try:
    from pydantic import BaseModel
except ImportError:
    raise ImportError("pydantic is required for the ashru pydantic adapter. Run `pip install ashru[pydantic]`")

from . import parse, Verb

T = TypeVar('T', bound=BaseModel)

class AshruPydanticAdapter(Generic[T]):
    def __init__(self, model: Type[T]):
        self.model = model
        self.fields = list(self.model.model_fields.keys())
        
    def prompt(self) -> str:
        """Returns the LLM prompt instruction for this model."""
        cols_str = "|".join(self.fields)
        return (
            f"Return ASHRU/1 format — one V| line per fact.\n"
            f"Ensure the positional columns match exactly: V|{cols_str}"
        )
        
    def parse(self, text: str, strict: bool = False) -> List[T]:
        """Parses ASHRU output into Pydantic models."""
        doc = parse(text, strict=strict)
        results = []
        for verb in doc.verbs:
            data: dict[str, Any] = {}
            for field in self.fields:
                if field == 'verb' or field == 'verb_lemma':
                    data[field] = verb.verb_lemma
                elif hasattr(verb, field):
                    data[field] = getattr(verb, field)
                elif field in verb.attributes:
                    data[field] = verb.attributes[field]
            try:
                results.append(self.model.model_validate(data))
            except Exception as e:
                if strict:
                    raise ValueError(f"Pydantic validation failed for row: {e}")
                # otherwise skip malformed objects
        return results

def as_ashru(model: Type[T]) -> AshruPydanticAdapter[T]:
    """Wraps a Pydantic BaseModel to provide ASHRU prompt generation and parsing."""
    return AshruPydanticAdapter(model)
