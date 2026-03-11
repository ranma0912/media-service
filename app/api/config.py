"""
配置管理 API
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, Optional
from loguru import logger

from app.core.config import config_manager

router = APIRouter()


class ConfigUpdate(BaseModel):
    """配置更新"""
    key: str
    value: Any


class ConfigResponse(BaseModel):
    """配置响应"""
    key: str
    value: Any


@router.get("/")
async def get_config():
    """获取完整配置（脱敏）"""
    config = config_manager.config
    config_dict = config.model_dump(mode='json')

    # 脱敏处理
    sensitive_keys = ['api_key', 'password', 'secret', 'token']
    for key in sensitive_keys:
        if key in str(config_dict):
            # 简单脱敏，实际应更精确
            config_dict = _mask_sensitive_values(config_dict, key)

    return config_dict


def _mask_sensitive_values(data: Any, key: str) -> Any:
    """递归脱敏敏感值"""
    if isinstance(data, dict):
        return {k: _mask_sensitive_values(v, key) if k.lower() != key else "***" 
                for k, v in data.items()}
    elif isinstance(data, list):
        return [_mask_sensitive_values(item, key) for item in data]
    return data


@router.get("/{key}")
async def get_config_value(key: str):
    """获取单个配置项"""
    config = config_manager.config
    config_dict = config.model_dump(mode='json')

    # 支持嵌套键访问，如 "server.port"
    keys = key.split('.')
    value = config_dict
    for k in keys:
        if isinstance(value, dict) and k in value:
            value = value[k]
        else:
            raise HTTPException(status_code=404, detail=f"配置项不存在: {key}")

    # 脱敏敏感信息
    sensitive_keys = ['api_key', 'password', 'secret', 'token']
    if any(s in key.lower() for s in sensitive_keys):
        value = "***"

    return ConfigResponse(key=key, value=value)


@router.put("/{key}")
async def update_config_value(update: ConfigUpdate):
    """更新配置项"""
    config = config_manager.load()
    config_dict = config.model_dump(mode='json')

    # 支持嵌套键更新
    keys = update.key.split('.')
    current = config_dict
    for k in keys[:-1]:
        if k not in current:
            current[k] = {}
        current = current[k]

    # 更新值
    current[keys[-1]] = update.value

    # 保存配置
    try:
        config_manager.save(config)
        logger.info(f"配置已更新: {update.key}")
        return {"success": True, "message": "配置更新成功"}
    except Exception as e:
        logger.error(f"配置更新失败: {e}")
        raise HTTPException(status_code=500, detail=f"配置更新失败: {str(e)}")


@router.post("/reload")
async def reload_config():
    """重新加载配置"""
    try:
        config_manager.reload()
        logger.info("配置已重新加载")
        return {"success": True, "message": "配置重新加载成功"}
    except Exception as e:
        logger.error(f"配置重新加载失败: {e}")
        raise HTTPException(status_code=500, detail=f"配置重新加载失败: {str(e)}")


@router.get("/naming-rules")
async def get_naming_rules():
    """获取命名规则"""
    rules = config_manager.load_naming_rules()
    return rules


@router.put("/naming-rules")
async def update_naming_rules(rules: Dict[str, Any]):
    """更新命名规则"""
    try:
        config_manager.save_naming_rules(rules)
        logger.info("命名规则已更新")
        return {"success": True, "message": "命名规则更新成功"}
    except Exception as e:
        logger.error(f"命名规则更新失败: {e}")
        raise HTTPException(status_code=500, detail=f"命名规则更新失败: {str(e)}")
