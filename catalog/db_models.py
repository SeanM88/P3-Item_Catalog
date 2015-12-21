from sqlalchemy import Column, ForeignKey, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine

from datetime import datetime
 
Base = declarative_base()

class User(Base):
    __tablename__ = 'user'
   
    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)
    email = Column(String(250), nullable=False)
    picture = Column(String(500))

    @property
    def serialize(self):
        """Return object data in easily serializeable format"""
        return {
            'id'           : self.id,
            'name'         : self.name,
            'email'        : self.email,
            'picture'      : self.picture,
        }

class Category(Base):
    __tablename__ = 'category'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(120), nullable=False)
    description = Column(String(500))
    user_id = Column(Integer,ForeignKey('user.id'))
    user = relationship(User)

    @property
    def serialize(self):
        """Return object data in easily serializeable format"""
        return {
             'id'            : self.id,
             'name'          : self.name,
             'description'   : self.description,
        }
 
class Item(Base):
    __tablename__ = 'item'
    
    id = Column(Integer, primary_key = True)
    created_on = Column(DateTime, default = datetime.now)
    last_modified = Column(DateTime, onupdate = datetime.now, default = datetime.now)
    name = Column(String(120), nullable = False)
    description = Column(String(500))
    price = Column(String(12))
    image = Column(String(300))
    category_id = Column(Integer,ForeignKey('category.id'))
    category = relationship(Category)
    category_name = Column(String(120))
    user_id = Column(Integer,ForeignKey('user.id'))
    user = relationship(User)


    @property
    def serialize(self):
        """Return object data in easily serializeable format"""
        return {
            'id'            : self.id,
            'name'          : self.name,
            'description'   : self.description,
            'price'         : self.price,
            'image'         : self.image,
            'category_id'   : self.category_id,
            'category_name' : self.category_name,
            'created_on'    : self.created_on.strftime('%I:%M:%S%p on %B, %d %Y'),
            'last_modified' : self.last_modified.strftime('%I:%M:%S%p on %B, %d %Y')
        }


engine = create_engine('sqlite:///catalogapp.db')
 
Base.metadata.create_all(engine)