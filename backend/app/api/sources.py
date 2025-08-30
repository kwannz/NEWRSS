"""
RSS源管理API
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from app.core.database import get_db
from app.models.news import NewsSource

router = APIRouter(prefix="/sources", tags=["sources"])

class NewsSourceResponse(BaseModel):
    id: int
    name: str
    url: str
    source_type: str
    category: str
    is_active: bool
    fetch_interval: int
    last_fetched: Optional[str] = None
    priority: int
    created_at: str
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True

class NewsSourceCreate(BaseModel):
    name: str
    url: str
    source_type: str
    category: str
    priority: int = 1
    fetch_interval: int = 1800
    is_active: bool = True

class NewsSourceUpdate(BaseModel):
    url: Optional[str] = None
    source_type: Optional[str] = None
    category: Optional[str] = None
    priority: Optional[int] = None
    fetch_interval: Optional[int] = None
    is_active: Optional[bool] = None

@router.get("/", response_model=List[NewsSourceResponse])
async def list_sources(
    category: Optional[str] = Query(None, description="过滤分类"),
    active_only: bool = Query(True, description="仅显示活跃源"),
    db: AsyncSession = Depends(get_db)
):
    """获取所有RSS源列表"""
    query = select(NewsSource)
    
    if category:
        query = query.where(NewsSource.category == category)
    if active_only:
        query = query.where(NewsSource.is_active == True)
    
    query = query.order_by(NewsSource.priority.desc(), NewsSource.name)
    
    result = await db.execute(query)
    sources = result.scalars().all()
    
    return [
        NewsSourceResponse(
            id=source.id,
            name=source.name,
            url=source.url,
            source_type=source.source_type,
            category=source.category,
            is_active=source.is_active,
            fetch_interval=source.fetch_interval,
            last_fetched=source.last_fetched.isoformat() if source.last_fetched else None,
            priority=source.priority,
            created_at=source.created_at.isoformat(),
            updated_at=source.updated_at.isoformat() if source.updated_at else None
        )
        for source in sources
    ]

@router.get("/categories")
async def get_categories(db: AsyncSession = Depends(get_db)):
    """获取所有分类"""
    result = await db.execute(
        select(NewsSource.category).distinct().where(NewsSource.is_active == True)
    )
    categories = [row[0] for row in result.fetchall()]
    return {"categories": categories}

@router.get("/stats")
async def get_source_stats(db: AsyncSession = Depends(get_db)):
    """获取RSS源统计信息"""
    # 总数
    total_result = await db.execute(select(NewsSource))
    total_count = len(total_result.scalars().all())
    
    # 活跃数
    active_result = await db.execute(
        select(NewsSource).where(NewsSource.is_active == True)
    )
    active_count = len(active_result.scalars().all())
    
    # 按分类统计
    category_result = await db.execute(
        select(NewsSource.category, NewsSource.id).where(NewsSource.is_active == True)
    )
    categories = {}
    for category, _ in category_result.fetchall():
        categories[category] = categories.get(category, 0) + 1
    
    # 按类型统计
    type_result = await db.execute(
        select(NewsSource.source_type, NewsSource.id).where(NewsSource.is_active == True)
    )
    types = {}
    for source_type, _ in type_result.fetchall():
        types[source_type] = types.get(source_type, 0) + 1
    
    return {
        "total": total_count,
        "active": active_count,
        "inactive": total_count - active_count,
        "by_category": categories,
        "by_type": types
    }

@router.post("/", response_model=NewsSourceResponse)
async def create_source(
    source: NewsSourceCreate,
    db: AsyncSession = Depends(get_db)
):
    """创建新的RSS源"""
    # 检查名称是否已存在
    existing = await db.execute(
        select(NewsSource).where(NewsSource.name == source.name)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Source name already exists")
    
    # 检查URL是否已存在
    existing_url = await db.execute(
        select(NewsSource).where(NewsSource.url == source.url)
    )
    if existing_url.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Source URL already exists")
    
    db_source = NewsSource(
        name=source.name,
        url=source.url,
        source_type=source.source_type,
        category=source.category,
        priority=source.priority,
        fetch_interval=source.fetch_interval,
        is_active=source.is_active,
        created_at=datetime.utcnow()
    )
    
    db.add(db_source)
    await db.commit()
    await db.refresh(db_source)
    
    return NewsSourceResponse(
        id=db_source.id,
        name=db_source.name,
        url=db_source.url,
        source_type=db_source.source_type,
        category=db_source.category,
        is_active=db_source.is_active,
        fetch_interval=db_source.fetch_interval,
        last_fetched=db_source.last_fetched.isoformat() if db_source.last_fetched else None,
        priority=db_source.priority,
        created_at=db_source.created_at.isoformat(),
        updated_at=db_source.updated_at.isoformat() if db_source.updated_at else None
    )

@router.put("/{source_id}", response_model=NewsSourceResponse)
async def update_source(
    source_id: int,
    source_update: NewsSourceUpdate,
    db: AsyncSession = Depends(get_db)
):
    """更新RSS源"""
    result = await db.execute(
        select(NewsSource).where(NewsSource.id == source_id)
    )
    db_source = result.scalar_one_or_none()
    
    if not db_source:
        raise HTTPException(status_code=404, detail="Source not found")
    
    # 更新字段
    update_data = source_update.dict(exclude_unset=True)
    if update_data:
        update_data["updated_at"] = datetime.utcnow()
        await db.execute(
            update(NewsSource)
            .where(NewsSource.id == source_id)
            .values(**update_data)
        )
        await db.commit()
        await db.refresh(db_source)
    
    return NewsSourceResponse(
        id=db_source.id,
        name=db_source.name,
        url=db_source.url,
        source_type=db_source.source_type,
        category=db_source.category,
        is_active=db_source.is_active,
        fetch_interval=db_source.fetch_interval,
        last_fetched=db_source.last_fetched.isoformat() if db_source.last_fetched else None,
        priority=db_source.priority,
        created_at=db_source.created_at.isoformat(),
        updated_at=db_source.updated_at.isoformat() if db_source.updated_at else None
    )

@router.delete("/{source_id}")
async def delete_source(
    source_id: int,
    db: AsyncSession = Depends(get_db)
):
    """删除RSS源"""
    result = await db.execute(
        select(NewsSource).where(NewsSource.id == source_id)
    )
    db_source = result.scalar_one_or_none()
    
    if not db_source:
        raise HTTPException(status_code=404, detail="Source not found")
    
    await db.execute(
        delete(NewsSource).where(NewsSource.id == source_id)
    )
    await db.commit()
    
    return {"message": f"Source '{db_source.name}' deleted successfully"}

@router.post("/{source_id}/toggle")
async def toggle_source(
    source_id: int,
    db: AsyncSession = Depends(get_db)
):
    """切换RSS源的激活状态"""
    result = await db.execute(
        select(NewsSource).where(NewsSource.id == source_id)
    )
    db_source = result.scalar_one_or_none()
    
    if not db_source:
        raise HTTPException(status_code=404, detail="Source not found")
    
    new_status = not db_source.is_active
    await db.execute(
        update(NewsSource)
        .where(NewsSource.id == source_id)
        .values(is_active=new_status, updated_at=datetime.utcnow())
    )
    await db.commit()
    
    return {
        "message": f"Source '{db_source.name}' {'activated' if new_status else 'deactivated'}",
        "is_active": new_status
    }