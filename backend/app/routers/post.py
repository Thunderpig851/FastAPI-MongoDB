from cgitb import lookup
from datetime import datetime
from fastapi import Depends, HTTPException, status, APIRouter, Response
from pymongo.collection import ReturnDocument
from app import schemas
from app.database import Post
from app.oauth2 import require_user
from app.serializers.postSerializers import postEntity, postListEntity
from bson.objectid import ObjectId

router = APIRouter()

@router.get('/')
def get_posts(limit: int = 10, page: int = 1, search = '', user_id: str = Depends(require_user)):
    skip = (page - 1) * limit
    pipeline = [
        {'$match': {}},
        {'$lookup': {'from': 'users', 'localField': 'user',
                     'foreignField': '_id', 'as': 'user'}},
        {'$unwind': '$user'},
        {
            '$skip': skip
        },
        {
            '$limit': limit
        }
    ]
    posts =  postListEntity(Post.aggregate(pipeline))
    return {'status': 'success', 'results': len(posts), 'posts': posts}

@router.post('/', status_code=status.HTTP_201_CREATED)
def create_post(post: schemas.CreatePostSchema, user_id: str = Depends(require_user)):
    post.user = ObjectId(user_id)
    post.created_at = datetime.utcnow()
    post.updated_at = post.created_at
    result = Post.insert_one(post.dict())
    pipeline = [
        {'$match': {'_id': result.inserted_id}},
        {'$lookup': {'from': 'users', 'localField': 'user',
                     'foreignField': '_id', 'as': 'user'}},
        {'$unwind': '$user'},
    ]
    new_post = postListEntity(Post.aggregate(pipeline))[0]
    return new_post

@router.put('/{id}')
def update_post(id: str, payload: schemas.UpdatePostSchema, user_id: str = Depends(require_user)):
    if not ObjectId.is_valid(id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f'Id {id} not valid')
    updated_post = Post.find_ond_and_update(
                            {'_id': ObjectId(id)}, 
                            {'$set': payload.dict(exclude_none=True)},
                            return_document=ReturnDocument.AFTER)
    if not updated_post:
        raise HTTPException(status_code=status.HTTP_200_OK,
                            detail=f'Post with id {id} not found')
    return postEntity(updated_post)

@router.get('/{id}')
def get_post(id: str, user_id: str = Depends(require_user)):
    if not ObjectId.is_valid(id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f'Id {id} not valid')
    pipeline = [
        {'$match': {'_id': ObjectId(id)}},
        {'$lookup': {'from': 'users', 'localField': 'user',
                    'foreignField': '_id', 'as': 'user'}},
        {'$unwind': '$user'},
    ]
    post = postListEntity(Post.aggregate(pipeline))[0]
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f'Post with id {id} not found')
    return post

@router.delete('/{id}')
def delete_post(id: str, user_id: str = Depends(require_user)):
    if not ObjectId.is_valid(id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f'Id {id} not valid')
    post = Post.find_one_and_delete({'_id': ObjectId(id)})
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f'Post with id {id} not found')
    return Response(status_code=status.HTTP_204_NO_CONTENT)
