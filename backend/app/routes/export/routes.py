"""Export API route handlers."""
import re
from uuid import UUID
from datetime import datetime
from io import BytesIO
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import or_
from sqlalchemy.orm import Session
import xlsxwriter

from app.database import get_db
from app.models import Estimate, User
from app.models.sharing import Sharing
from app.auth import get_current_user
from .helpers import _check_estimate_access
from .excel_builder import build_estimate_excel

router = APIRouter(prefix="/export", tags=["export"])


@router.get("/estimate/{estimate_id}/excel")
def export_estimate_to_excel(
    estimate_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Export an estimate to Excel format with professional RFP-ready layout."""
    try:
        estimate = _check_estimate_access(estimate_id, current_user, db)
        line_items = sorted(estimate.line_items, key=lambda x: x.display_order or 0)
        cloud = (getattr(estimate, 'cloud', 'aws') or 'aws').lower()
        region = getattr(estimate, 'region', 'us-east-1') or 'us-east-1'
        tier = getattr(estimate, 'tier', 'PREMIUM') or 'PREMIUM'

        output = build_estimate_excel(estimate, line_items, cloud, region, tier, db=db)

        estimate_name = getattr(estimate, 'estimate_name', 'Untitled') or 'Untitled'
        safe_name = re.sub(r'[^a-zA-Z0-9_]', '_', estimate_name)[:50]
        filename = f"Databricks_Estimate_{safe_name}_{datetime.now().strftime('%Y%m%d')}.xlsx"

        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Export error: {str(e)}")


@router.get("/estimates/excel")
def export_all_estimates_to_excel(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Export all estimates summary to Excel."""
    shared_estimate_ids = db.query(Sharing.estimate_id).filter(
        Sharing.shared_with_user_id == current_user.user_id
    ).subquery()

    estimates = db.query(Estimate).filter(
        Estimate.is_deleted == False,
        or_(
            Estimate.owner_user_id == current_user.user_id,
            Estimate.estimate_id.in_(shared_estimate_ids)
        )
    ).order_by(Estimate.updated_at.desc()).all()

    output = BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})

    header_format = workbook.add_format({
        'bold': True, 'bg_color': '#f97316', 'font_color': 'white', 'border': 1
    })
    cell_format = workbook.add_format({'border': 1})

    sheet = workbook.add_worksheet('All Estimates')

    headers = ['Estimate Name', 'Cloud', 'Region', 'Tier', 'Status', 'Version', 'Created', 'Updated']
    widths_list = [40, 15, 20, 15, 15, 10, 20, 20]

    for i, width in enumerate(widths_list):
        sheet.set_column(i, i, width)
    for col, header in enumerate(headers):
        sheet.write(0, col, header, header_format)

    for r, est in enumerate(estimates, start=1):
        created = getattr(est, 'created_at', '') or ''
        updated = getattr(est, 'updated_at', '') or ''
        if isinstance(created, datetime):
            created = created.strftime('%Y-%m-%d %H:%M')
        if isinstance(updated, datetime):
            updated = updated.strftime('%Y-%m-%d %H:%M')

        sheet.write(r, 0, getattr(est, 'estimate_name', '') or '', cell_format)
        sheet.write(r, 1, getattr(est, 'cloud', '') or '', cell_format)
        sheet.write(r, 2, getattr(est, 'region', '') or '', cell_format)
        sheet.write(r, 3, getattr(est, 'tier', '') or '', cell_format)
        sheet.write(r, 4, getattr(est, 'status', '') or '', cell_format)
        sheet.write(r, 5, getattr(est, 'version', 1), cell_format)
        sheet.write(r, 6, created, cell_format)
        sheet.write(r, 7, updated, cell_format)

    workbook.close()
    output.seek(0)

    filename = f"Databricks_Estimates_Export_{datetime.now().strftime('%Y%m%d')}.xlsx"

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )
