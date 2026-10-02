# Contributing

Use a feature branch and pull request. Keep data-mutation changes accompanied by
negative tests, migration review, and API-schema coverage.

Before opening a pull request, run:

```bash
python -m pytest
ruff format --check src tests
ruff check src tests
mypy src
python -m build
twine check dist/*
```

Never commit production datasets, uploaded files, API tokens, or `.env` files.
