from main import SessionLocal, User, Conversation, Message, Group, GroupMember
import uuid

db = SessionLocal()

db.query(Message).delete()
db.query(GroupMember).delete()
db.query(Group).delete()
db.query(Conversation).delete()
db.query(User).delete()
db.commit()

# Users
u1 = User(username="alice", display_name="Alice", is_online=True)
u2 = User(username="bob", display_name="Bob", is_online=True)
u3 = User(username="charlie", display_name="Charlie", is_online=True)

db.add_all([u1, u2, u3])
db.commit()

# 1-on-1 conversation
conv = Conversation(user1_id=u1.id, user2_id=u2.id)
db.add(conv)
db.commit()

# Messages in conversation
for i in range(5):
    m = Message(sender_id=u1.id if i%2==0 else u2.id, conversation_id=conv.id, content=f"Hello {i+1}")
    db.add(m)
db.commit()

# Group
group = Group(name="Dev Team", created_by=u1.id)
db.add(group)
db.commit()

for uid in [u1.id, u2.id, u3.id]:
    gm = GroupMember(group_id=group.id, user_id=uid)
    db.add(gm)
db.commit()

# Group messages
for i in range(3):
    m = Message(sender_id=u1.id if i%2==0 else u2.id, group_id=group.id, content=f"Team msg {i+1}")
    db.add(m)
db.commit()

print("✓ Seeded: alice, bob, charlie + conversations + groups")
db.close()