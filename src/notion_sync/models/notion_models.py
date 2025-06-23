"""
Data models for Notion entities.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from enum import Enum


class NotionObjectType(Enum):
    """Notion object types."""
    PAGE = "page"
    DATABASE = "database"
    BLOCK = "block"
    USER = "user"


class BlockType(Enum):
    """Notion block types."""
    PARAGRAPH = "paragraph"
    HEADING_1 = "heading_1"
    HEADING_2 = "heading_2"
    HEADING_3 = "heading_3"
    BULLETED_LIST_ITEM = "bulleted_list_item"
    NUMBERED_LIST_ITEM = "numbered_list_item"
    TO_DO = "to_do"
    TOGGLE = "toggle"
    CHILD_PAGE = "child_page"
    CHILD_DATABASE = "child_database"
    EMBED = "embed"
    IMAGE = "image"
    VIDEO = "video"
    FILE = "file"
    PDF = "pdf"
    BOOKMARK = "bookmark"
    CALLOUT = "callout"
    QUOTE = "quote"
    EQUATION = "equation"
    DIVIDER = "divider"
    TABLE_OF_CONTENTS = "table_of_contents"
    COLUMN = "column"
    COLUMN_LIST = "column_list"
    LINK_PREVIEW = "link_preview"
    SYNCED_BLOCK = "synced_block"
    TEMPLATE = "template"
    LINK_TO_PAGE = "link_to_page"
    TABLE = "table"
    TABLE_ROW = "table_row"
    UNSUPPORTED = "unsupported"


@dataclass
class NotionUser:
    """Represents a Notion user."""
    id: str
    name: Optional[str] = None
    avatar_url: Optional[str] = None
    type: str = "person"
    person_email: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'NotionUser':
        """Create NotionUser from API response."""
        person = data.get("person", {})
        return cls(
            id=data["id"],
            name=data.get("name"),
            avatar_url=data.get("avatar_url"),
            type=data.get("type", "person"),
            person_email=person.get("email")
        )


@dataclass
class NotionParent:
    """Represents a Notion parent reference."""
    type: str
    page_id: Optional[str] = None
    database_id: Optional[str] = None
    workspace: bool = False
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'NotionParent':
        """Create NotionParent from API response."""
        return cls(
            type=data["type"],
            page_id=data.get("page_id"),
            database_id=data.get("database_id"),
            workspace=data.get("workspace", False)
        )


@dataclass
class NotionRichText:
    """Represents Notion rich text."""
    type: str
    text: Optional[str] = None
    plain_text: str = ""
    href: Optional[str] = None
    annotations: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'NotionRichText':
        """Create NotionRichText from API response."""
        text_content = data.get("text", {})
        return cls(
            type=data["type"],
            text=text_content.get("content"),
            plain_text=data.get("plain_text", ""),
            href=text_content.get("link", {}).get("url") if text_content.get("link") else None,
            annotations=data.get("annotations", {})
        )


@dataclass
class NotionProperty:
    """Represents a Notion property."""
    id: str
    name: str
    type: str
    value: Any = None
    
    @classmethod
    def from_dict(cls, name: str, data: Dict[str, Any]) -> 'NotionProperty':
        """Create NotionProperty from API response."""
        return cls(
            id=data.get("id", ""),
            name=name,
            type=data["type"],
            value=data.get(data["type"])
        )


@dataclass
class NotionBlock:
    """Represents a Notion block."""
    id: str
    type: str
    created_time: datetime
    last_edited_time: datetime
    created_by: NotionUser
    last_edited_by: NotionUser
    has_children: bool = False
    archived: bool = False
    content: Dict[str, Any] = field(default_factory=dict)
    children: List['NotionBlock'] = field(default_factory=list)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'NotionBlock':
        """Create NotionBlock from API response."""
        return cls(
            id=data["id"],
            type=data["type"],
            created_time=datetime.fromisoformat(data["created_time"].replace("Z", "+00:00")),
            last_edited_time=datetime.fromisoformat(data["last_edited_time"].replace("Z", "+00:00")),
            created_by=NotionUser.from_dict(data["created_by"]),
            last_edited_by=NotionUser.from_dict(data["last_edited_by"]),
            has_children=data.get("has_children", False),
            archived=data.get("archived", False),
            content=data.get(data["type"], {})
        )
    
    def get_text_content(self) -> str:
        """Extract plain text content from the block."""
        if self.type in ["paragraph", "heading_1", "heading_2", "heading_3", "bulleted_list_item", "numbered_list_item"]:
            rich_text = self.content.get("rich_text", [])
            return "".join([rt.get("plain_text", "") for rt in rich_text])
        elif self.type == "to_do":
            rich_text = self.content.get("rich_text", [])
            text = "".join([rt.get("plain_text", "") for rt in rich_text])
            checked = self.content.get("checked", False)
            return f"{'[x]' if checked else '[ ]'} {text}"
        elif self.type == "callout":
            rich_text = self.content.get("rich_text", [])
            return "".join([rt.get("plain_text", "") for rt in rich_text])
        elif self.type == "quote":
            rich_text = self.content.get("rich_text", [])
            return "".join([rt.get("plain_text", "") for rt in rich_text])
        return ""


@dataclass
class NotionPage:
    """Represents a Notion page."""
    id: str
    created_time: datetime
    last_edited_time: datetime
    created_by: NotionUser
    last_edited_by: NotionUser
    cover: Optional[Dict[str, Any]] = None
    icon: Optional[Dict[str, Any]] = None
    parent: Optional[NotionParent] = None
    archived: bool = False
    properties: Dict[str, NotionProperty] = field(default_factory=dict)
    url: str = ""
    public_url: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'NotionPage':
        """Create NotionPage from API response."""
        properties = {}
        for name, prop_data in data.get("properties", {}).items():
            properties[name] = NotionProperty.from_dict(name, prop_data)
        
        return cls(
            id=data["id"],
            created_time=datetime.fromisoformat(data["created_time"].replace("Z", "+00:00")),
            last_edited_time=datetime.fromisoformat(data["last_edited_time"].replace("Z", "+00:00")),
            created_by=NotionUser.from_dict(data["created_by"]),
            last_edited_by=NotionUser.from_dict(data["last_edited_by"]),
            cover=data.get("cover"),
            icon=data.get("icon"),
            parent=NotionParent.from_dict(data["parent"]) if data.get("parent") else None,
            archived=data.get("archived", False),
            properties=properties,
            url=data.get("url", ""),
            public_url=data.get("public_url")
        )
    
    def get_title(self) -> str:
        """Get the page title."""
        for prop in self.properties.values():
            if prop.type == "title" and prop.value:
                rich_text = prop.value.get("rich_text", [])
                return "".join([rt.get("plain_text", "") for rt in rich_text])
        return "Untitled"


@dataclass
class NotionDatabase:
    """Represents a Notion database."""
    id: str
    created_time: datetime
    last_edited_time: datetime
    created_by: NotionUser
    last_edited_by: NotionUser
    title: List[NotionRichText] = field(default_factory=list)
    description: List[NotionRichText] = field(default_factory=list)
    icon: Optional[Dict[str, Any]] = None
    cover: Optional[Dict[str, Any]] = None
    properties: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    parent: Optional[NotionParent] = None
    url: str = ""
    archived: bool = False
    is_inline: bool = False
    public_url: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'NotionDatabase':
        """Create NotionDatabase from API response."""
        title = [NotionRichText.from_dict(rt) for rt in data.get("title", [])]
        description = [NotionRichText.from_dict(rt) for rt in data.get("description", [])]
        
        return cls(
            id=data["id"],
            created_time=datetime.fromisoformat(data["created_time"].replace("Z", "+00:00")),
            last_edited_time=datetime.fromisoformat(data["last_edited_time"].replace("Z", "+00:00")),
            created_by=NotionUser.from_dict(data["created_by"]),
            last_edited_by=NotionUser.from_dict(data["last_edited_by"]),
            title=title,
            description=description,
            icon=data.get("icon"),
            cover=data.get("cover"),
            properties=data.get("properties", {}),
            parent=NotionParent.from_dict(data["parent"]) if data.get("parent") else None,
            url=data.get("url", ""),
            archived=data.get("archived", False),
            is_inline=data.get("is_inline", False),
            public_url=data.get("public_url")
        )
    
    def get_title_text(self) -> str:
        """Get the database title as plain text."""
        return "".join([rt.plain_text for rt in self.title])


@dataclass
class SyncMetadata:
    """Metadata for synchronization tracking."""
    local_path: str
    notion_id: str
    last_sync_time: datetime
    local_modified_time: datetime
    notion_modified_time: datetime
    sync_direction: str  # "local_to_notion", "notion_to_local", "bidirectional"
    checksum: str = ""
    conflict_status: str = "none"  # "none", "detected", "resolved"
    
    def has_local_changes(self) -> bool:
        """Check if local file has changes since last sync."""
        return self.local_modified_time > self.last_sync_time
    
    def has_notion_changes(self) -> bool:
        """Check if Notion content has changes since last sync."""
        return self.notion_modified_time > self.last_sync_time
    
    def has_conflict(self) -> bool:
        """Check if there's a sync conflict."""
        return self.has_local_changes() and self.has_notion_changes()
