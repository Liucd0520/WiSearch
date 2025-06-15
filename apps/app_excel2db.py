from tools.excel2db import excel2db
from fastapi import FastAPI, APIRouter
from typing import List, Optional
import tempfile
from pydantic import BaseModel
from enum import Enum
from fastapi import File, UploadFile
import os

router = APIRouter()

# async def Excel2DataBase(request: ModelConfig, file: UploadFile = File(...))

@router.post('/', summary='上传Excel文件并存入到数据库中')
async def Excel2DataBase(mysql_uri: str = 'mysql+pymysql://root:liucd123@localhost:3306/db_TEMP',
                         table_names: str = 't_temp',
                          file: UploadFile = File(...)):
    # 将file文件存储到某个临时文件夹内，并返回文件路径
    

    temp_dir = tempfile.TemporaryDirectory(prefix='temp_', dir='tmp')
    file_path = f'{temp_dir.name}/{file.filename}'
    with open(file_path, 'wb') as f:
        f.write(file.file.read())
        print(f'文件写入{file_path} 完成')

    excel2db(file_path,table_names, mysql_uri)

    return {'message': 'Excel文件已存入数据库'}
