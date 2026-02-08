# Global Guidelines

## Javascript

### Framework Preferences

- Unless otherwise specified within the repository, opt to use Vercel-friendly technologies.

### Coding Style

- Prefer `const x = ...` over `function x(...)` wherever possible.

## Python

### Project Organization

- Favor package-first layouts with stable import paths.
- Organize by domain/capability first, then by technical role.
- Keep modules focused; one file should usually have one primary responsibility.
- Design dependency flow in one direction and avoid upward imports.
- Keep pure business/domain logic separate from infrastructure (I/O, network, DB, CLI, framework glue).
- Keep framework entrypoints thin; they should parse/validate inputs, call library code, and format outputs.
- Prefer composition over deep inheritance hierarchies.
- Use explicit interfaces (Protocol/ABC) at subsystem boundaries when multiple implementations are expected.
- Keep shared utilities narrow and intentional; avoid a catch-all `utils` module.
- Centralize config schemas/defaults, and keep config objects separate from runtime side effects.
- Keep top-level directories predictable:
  - `src/<pkg>/` or `<pkg>/` for application/library code.
  - `tests/` mirroring package structure.
  - `scripts/` for development and maintenance tasks.
  - `examples/` for demos only.
- Treat public APIs as intentional:
  - Export stable APIs explicitly in `__init__.py`.
  - Keep internals private by default.
  - Update docs/examples together with public API changes.

### Machine Learning

- When useful, use `chex` at the start of a function to do runtime validation on the function's input values.
- Follow Noam Shazeer's tensor name suffix convention when writing Jax, PyTorch, Tensorflow or Numpy code. This means that, wherever possible, tensor names should be written as `name_bt3` or similar, where `_bt3` represents the tensor dimensions, for example, `b` for batch size, `t` for time, and `3` for a fixed channel dimension.
- Prefer `idx` over `i` or `index`. Similarly, `for ... in` statements should use variable names that are descriptive.
- Use `bsz` and `tsz` for tensor batch and time dimension sizes.
- Don't use capital letters in variable names, even for annotating tensor dimensions. If the letter used to denote the tensor dimension is ambiguous, we can add a comment or docstring message to explain it.

### Coding Style

- Follow Google's Python style guide as closely as possible.
- Don't add a new line after docstrings (Ruff D202).
- Almost every repository we're working with uses Python >= 3.11, so we should almost never use `typing.Dict`, `typing.List`, `typing.Union`, or similar - just use `dict`, `list`, `|` or whatever built-in notation.
- Similarly, we should use advanced Python typing semantics like Protocols to provide proper typechecking for complex components, if needed.
- Avoid using `typing.Any` as much as possible. If we do use it, we need to mark the line with `noqa: ANN401`
- Avoid `from __future__ import ...` statements, since we will always expect to use Python 3.11 or later.

### Comments

- Avoid having a comment before every line. Instead, have one longer comment followed by a block of code, usually a minimum of 3-5 lines (unless the line is very complicated and a comment would help clarify the thinking). Write comments assuming that the reader will be intelligent and care about the general structure of the code.
- For complex mathematically-oriented functions, include detailed math notation or explanatory diagrams in the docstring.
- Use docstrings for complex functions but avoid them for simple functions. Docstrings should include `Args` and `Returns` (unless nothing is returned).

### Linting

- Run `ruff check` and `ty lint` to lint code.
- All our code should typecheck properly. We should avoid using ambiguous types as much as possible.
- When fixing lint issues, think hard about the correct type and try to avoid using `# type: ignore`. Prefer to use `from typing import cast` for ambiguous types.

### Testing

- In general, we don't care about test coverage, since most of the code we write is fairly technical. We therefore don't need to implement lots of redundant tests.
- For machine learning code, we should implement tests for the correctness of the core mathematical functionality, which requires some amount of careful thought.
- When writing tests, use pytest functions. Avoid doing `class TestX:` unless it's absolutely necessary.

### Logging

- Avoid using `print` statements as much as possible. Instead, use the `colorlogging` module, which can be enabled when initializing a CLI using `colorlogging.configure()`. Use `logger = logging.getLogger(__name__)`, and and avoid using f-statements in log messages.
