"""Compatibility imports for older code paths.

The live URLs are registered from `stock_control`, `accounting_app`, and
`user_access`. This module intentionally re-exports those views so older
imports do not break while the project is being cleaned up.
"""

from accounting_app.views import (
    summary_create_view,
    summary_detail_view,
    summary_list_view,
    summary_pdf_view,
)
from stock_control.views import stock_sheet_pdf_view, stock_sheet_view
from user_access.views import WorkspaceLoginView, signup_view, workspace_home
