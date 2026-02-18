"""
Community Interaction Service

Service for managing community interactions including forums,
social features, and reputation systems.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class ContentType(str, Enum):
    """Types of community content."""
    POST = "post"
    COMMENT = "comment"
    DISCUSSION = "discussion"
    ANNOUNCEMENT = "announcement"
    QUESTION = "question"
    ANSWER = "answer"


class ReactionType(str, Enum):
    """Types of reactions."""
    LIKE = "like"
    HELPFUL = "helpful"
    INSIGHTFUL = "insightful"
    CELEBRATE = "celebrate"


@dataclass
class Reputation:
    """Reputation score for an agent."""
    agent_id: str
    score: float = 0.0
    level: int = 1
    badges: List[str] = field(default_factory=list)
    contributions: int = 0
    helpful_votes: int = 0
    created_at: float = field(default_factory=lambda: time.time())
    updated_at: float = field(default_factory=lambda: time.time())

    def calculate_level(self) -> int:
        """Calculate reputation level."""
        # Level increases every 100 points
        return max(1, int(self.score / 100) + 1)


@dataclass
class Content:
    """Community content."""
    id: str
    author_id: str
    type: ContentType
    title: Optional[str] = None
    body: str = ""
    parent_id: Optional[str] = None  # For comments/replies
    tags: List[str] = field(default_factory=list)
    reactions: Dict[ReactionType, List[str]] = field(default_factory=dict)  # type -> voter_ids
    view_count: int = 0
    is_pinned: bool = False
    is_locked: bool = False
    created_at: float = field(default_factory=lambda: time.time())
    updated_at: float = field(default_factory=lambda: time.time())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_reaction_count(self, reaction_type: ReactionType) -> int:
        """Get count of a specific reaction."""
        return len(self.reactions.get(reaction_type, []))

    def get_total_reactions(self) -> int:
        """Get total reactions."""
        return sum(len(voters) for voters in self.reactions.values())


@dataclass
class Follow:
    """Follow relationship."""
    follower_id: str
    following_id: str
    created_at: float = field(default_factory=lambda: time.time())


@dataclass
class Notification:
    """User notification."""
    id: str
    recipient_id: str
    type: str
    title: str
    body: str
    content_id: Optional[str] = None
    is_read: bool = False
    created_at: float = field(default_factory=lambda: time.time())


class CommunityInteractionService:
    """
    Community Interaction Service.

    Provides community features:
    - Content posting and discussions
    - Reactions and voting
    - Following and notifications
    - Reputation system
    - Badges and achievements
    """

    def __init__(self):
        """Initialize the Community Interaction Service."""
        # Storage
        self._contents: Dict[str, Content] = {}
        self._reputations: Dict[str, Reputation] = {}
        self._follows: Dict[str, List[Follow]] = {}  # follower_id -> follows
        self._notifications: Dict[str, List[Notification]] = {}  # recipient_id -> notifications

        # Indexes
        self._contents_by_author: Dict[str, List[str]] = {}
        self._contents_by_tag: Dict[str, List[str]] = {}

        # Callbacks
        self.on_content_created: Optional[Callable[[Content], None]] = None
        self.on_reaction: Optional[Callable[[str, str, ReactionType], None]] = None

    def create_content(
        self,
        author_id: str,
        type: ContentType,
        body: str,
        title: Optional[str] = None,
        parent_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Content:
        """
        Create community content.

        Args:
            author_id: Author agent ID
            type: Content type
            body: Content body
            title: Optional title
            parent_id: Parent content ID for replies
            tags: Content tags
            metadata: Additional metadata

        Returns:
            Created content
        """
        import uuid

        content = Content(
            id=str(uuid.uuid4())[:8],
            author_id=author_id,
            type=type,
            title=title,
            body=body,
            parent_id=parent_id,
            tags=tags or [],
            metadata=metadata or {},
        )

        self._contents[content.id] = content

        # Update indexes
        if author_id not in self._contents_by_author:
            self._contents_by_author[author_id] = []
        self._contents_by_author[author_id].append(content.id)

        for tag in content.tags:
            if tag not in self._contents_by_tag:
                self._contents_by_tag[tag] = []
            self._contents_by_tag[tag].append(content.id)

        # Update reputation
        self._add_reputation_points(author_id, 1)  # 1 point for creating content

        # Notify followers
        self._notify_followers(author_id, content)

        if self.on_content_created:
            self.on_content_created(content)

        logger.info(f"Content created: {content.id} by {author_id}")
        return content

    def get_content(self, content_id: str) -> Optional[Content]:
        """Get content by ID."""
        content = self._contents.get(content_id)
        if content:
            content.view_count += 1
        return content

    def update_content(
        self,
        content_id: str,
        author_id: str,
        body: Optional[str] = None,
        title: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> bool:
        """Update content."""
        content = self._contents.get(content_id)
        if not content or content.author_id != author_id:
            return False

        if body is not None:
            content.body = body
        if title is not None:
            content.title = title
        if tags is not None:
            # Update tag index
            for old_tag in content.tags:
                if old_tag in self._contents_by_tag:
                    self._contents_by_tag[old_tag].remove(content_id)
            for new_tag in tags:
                if new_tag not in self._contents_by_tag:
                    self._contents_by_tag[new_tag] = []
                self._contents_by_tag[new_tag].append(content_id)
            content.tags = tags

        content.updated_at = time.time()
        return True

    def delete_content(self, content_id: str, author_id: str) -> bool:
        """Delete content."""
        content = self._contents.get(content_id)
        if not content or content.author_id != author_id:
            return False

        # Remove from indexes
        if author_id in self._contents_by_author:
            self._contents_by_author[author_id].remove(content_id)

        for tag in content.tags:
            if tag in self._contents_by_tag:
                self._contents_by_tag[tag].remove(content_id)

        del self._contents[content_id]
        return True

    def add_reaction(
        self,
        content_id: str,
        voter_id: str,
        reaction_type: ReactionType,
    ) -> bool:
        """
        Add a reaction to content.

        Args:
            content_id: Content ID
            voter_id: Voter agent ID
            reaction_type: Type of reaction

        Returns:
            True if successful
        """
        content = self._contents.get(content_id)
        if not content:
            return False

        if content.author_id == voter_id:
            return False  # Can't react to own content

        # Initialize reaction type if needed
        if reaction_type not in content.reactions:
            content.reactions[reaction_type] = []

        # Check if already reacted
        if voter_id in content.reactions[reaction_type]:
            # Remove reaction (toggle)
            content.reactions[reaction_type].remove(voter_id)
            self._add_reputation_points(content.author_id, -1)
        else:
            # Add reaction
            content.reactions[reaction_type].append(voter_id)
            self._add_reputation_points(content.author_id, 1)

            # Special handling for helpful
            if reaction_type == ReactionType.HELPFUL:
                self._add_reputation_points(content.author_id, 5)
                reputation = self._reputations.get(content.author_id)
                if reputation:
                    reputation.helpful_votes += 1

        content.updated_at = time.time()

        if self.on_reaction:
            self.on_reaction(content_id, voter_id, reaction_type)

        return True

    def get_replies(self, content_id: str) -> List[Content]:
        """Get replies to content."""
        return [
            c for c in self._contents.values()
            if c.parent_id == content_id
        ]

    def get_discussion_thread(self, content_id: str) -> Dict[str, Any]:
        """Get full discussion thread."""
        content = self._contents.get(content_id)
        if not content:
            return {}

        def build_thread(c: Content) -> Dict[str, Any]:
            replies = self.get_replies(c.id)
            return {
                "content": c,
                "replies": [build_thread(r) for r in sorted(replies, key=lambda x: x.created_at)]
            }

        return build_thread(content)

    def list_content(
        self,
        type: Optional[ContentType] = None,
        author_id: Optional[str] = None,
        tag: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Content]:
        """List content with filters."""
        if tag and tag in self._contents_by_tag:
            content_ids = self._contents_by_tag[tag]
            contents = [self._contents[cid] for cid in content_ids if cid in self._contents]
        elif author_id and author_id in self._contents_by_author:
            content_ids = self._contents_by_author[author_id]
            contents = [self._contents[cid] for cid in content_ids if cid in self._contents]
        else:
            contents = list(self._contents.values())

        if type:
            contents = [c for c in contents if c.type == type]

        # Sort by creation time (newest first), pinned first
        contents.sort(key=lambda x: (not x.is_pinned, x.created_at), reverse=True)

        return contents[offset:offset + limit]

    def pin_content(self, content_id: str, admin_id: str) -> bool:
        """Pin content (admin action)."""
        content = self._contents.get(content_id)
        if not content:
            return False

        content.is_pinned = True
        content.updated_at = time.time()
        return True

    def lock_content(self, content_id: str, admin_id: str) -> bool:
        """Lock content from further replies (admin action)."""
        content = self._contents.get(content_id)
        if not content:
            return False

        content.is_locked = True
        content.updated_at = time.time()
        return True

    # Reputation System

    def get_reputation(self, agent_id: str) -> Reputation:
        """Get reputation for an agent."""
        if agent_id not in self._reputations:
            self._reputations[agent_id] = Reputation(agent_id=agent_id)
        return self._reputations[agent_id]

    def _add_reputation_points(self, agent_id: str, points: float) -> None:
        """Add reputation points to an agent."""
        reputation = self.get_reputation(agent_id)
        reputation.score = max(0, reputation.score + points)
        reputation.contributions += 1 if points > 0 else 0
        reputation.level = reputation.calculate_level()
        reputation.updated_at = time.time()

    def award_badge(self, agent_id: str, badge: str) -> bool:
        """Award a badge to an agent."""
        reputation = self.get_reputation(agent_id)
        if badge in reputation.badges:
            return False

        reputation.badges.append(badge)
        reputation.updated_at = time.time()

        # Notify
        self._add_notification(
            recipient_id=agent_id,
            type="badge_awarded",
            title="Badge Earned!",
            body=f"You have earned the '{badge}' badge!",
        )

        logger.info(f"Badge '{badge}' awarded to {agent_id}")
        return True

    def get_leaderboard(self, limit: int = 10) -> List[Reputation]:
        """Get reputation leaderboard."""
        reputations = list(self._reputations.values())
        reputations.sort(key=lambda x: x.score, reverse=True)
        return reputations[:limit]

    # Follow System

    def follow(self, follower_id: str, following_id: str) -> bool:
        """Follow an agent."""
        if follower_id == following_id:
            return False

        if follower_id not in self._follows:
            self._follows[follower_id] = []

        # Check if already following
        if any(f.following_id == following_id for f in self._follows[follower_id]):
            return False

        follow = Follow(follower_id=follower_id, following_id=following_id)
        self._follows[follower_id].append(follow)

        self._add_notification(
            recipient_id=following_id,
            type="new_follower",
            title="New Follower",
            body=f"{follower_id} started following you",
        )

        return True

    def unfollow(self, follower_id: str, following_id: str) -> bool:
        """Unfollow an agent."""
        if follower_id not in self._follows:
            return False

        for i, follow in enumerate(self._follows[follower_id]):
            if follow.following_id == following_id:
                self._follows[follower_id].pop(i)
                return True

        return False

    def get_followers(self, agent_id: str) -> List[str]:
        """Get list of followers."""
        followers = []
        for follower_id, follows in self._follows.items():
            if any(f.following_id == agent_id for f in follows):
                followers.append(follower_id)
        return followers

    def get_following(self, agent_id: str) -> List[str]:
        """Get list of agents being followed."""
        if agent_id not in self._follows:
            return []
        return [f.following_id for f in self._follows[agent_id]]

    def _notify_followers(self, author_id: str, content: Content) -> None:
        """Notify followers of new content."""
        followers = self.get_followers(author_id)

        for follower_id in followers:
            self._add_notification(
                recipient_id=follower_id,
                type="new_content",
                title=f"New post from {author_id}",
                body=content.title or content.body[:100],
                content_id=content.id,
            )

    # Notifications

    def _add_notification(
        self,
        recipient_id: str,
        type: str,
        title: str,
        body: str,
        content_id: Optional[str] = None,
    ) -> Notification:
        """Add a notification."""
        import uuid

        notification = Notification(
            id=str(uuid.uuid4())[:8],
            recipient_id=recipient_id,
            type=type,
            title=title,
            body=body,
            content_id=content_id,
        )

        if recipient_id not in self._notifications:
            self._notifications[recipient_id] = []
        self._notifications[recipient_id].append(notification)

        return notification

    def get_notifications(
        self,
        recipient_id: str,
        unread_only: bool = False,
        limit: int = 50,
    ) -> List[Notification]:
        """Get notifications for a user."""
        notifications = self._notifications.get(recipient_id, [])

        if unread_only:
            notifications = [n for n in notifications if not n.is_read]

        notifications.sort(key=lambda x: x.created_at, reverse=True)
        return notifications[:limit]

    def mark_notification_read(self, notification_id: str, recipient_id: str) -> bool:
        """Mark notification as read."""
        notifications = self._notifications.get(recipient_id, [])
        for notification in notifications:
            if notification.id == notification_id:
                notification.is_read = True
                return True
        return False

    def mark_all_read(self, recipient_id: str) -> int:
        """Mark all notifications as read."""
        notifications = self._notifications.get(recipient_id, [])
        count = 0
        for notification in notifications:
            if not notification.is_read:
                notification.is_read = True
                count += 1
        return count

    def get_community_stats(self) -> Dict[str, Any]:
        """Get community statistics."""
        total_content = len(self._contents)
        total_users = len(self._reputations)
        total_follows = sum(len(f) for f in self._follows.values())
        total_reactions = sum(
            c.get_total_reactions() for c in self._contents.values()
        )

        return {
            "total_content": total_content,
            "total_users": total_users,
            "total_follows": total_follows,
            "total_reactions": total_reactions,
            "content_by_type": {
                t.value: sum(1 for c in self._contents.values() if c.type == t)
                for t in ContentType
            },
            "top_tags": sorted(
                [(tag, len(ids)) for tag, ids in self._contents_by_tag.items()],
                key=lambda x: x[1],
                reverse=True
            )[:10],
        }
