# Global Guidelines

## Coding Style & Naming Conventions

- Use Noam Shazeer's tensor name suffix convention. Wherever possible, tensor names should be written as `name_bt3` or similar, where `_bt3` represents the tensor dimensions, for example, `b` for batch size, `t` for time, and `3` for a fixed channel dimension.
- Avoid having a comment before every line. Instead, have one longer comment followed by a block of code, usually a minimum of 3-5 lines (unless the line is very complicated and requires a longer explanation)
- Follow Google's Python style guide as closely as possible.
- Use docstrings for complex functions but avoid them for simple functions. Docstrings should include `Args` and `Returns` (unless nothing is returned).
