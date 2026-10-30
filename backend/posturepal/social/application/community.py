class Community:
    """Social use cases; activity sharing is always an explicit user action."""
    def __init__(self, repository):
        self.repository = repository

    def overview(self, user_id, offset=0):
        return {'feed':self.repository.feed(user_id,offset), 'friends':self.repository.connections(user_id),
                'privacy':self.repository.privacy(user_id), 'statistics':self.repository.stats(user_id)}

    def privacy(self,user_id,data): return self.repository.privacy(user_id,data)
    def request_friend(self,user_id,target): return self.repository.request_friend(user_id,target)
    def accept(self,user_id,target): return self.repository.accept(user_id,target)
    def remove(self,user_id,target): return self.repository.remove(user_id,target)
    def block(self,user_id,target,enabled): return self.repository.block(user_id,target,enabled)
    def publish(self,user_id,data): return self.repository.publish(user_id,data)
    def post(self,user_id,post_id): return self.repository.post(user_id,post_id)
    def edit_post(self,user_id,post_id,audience=None): return self.repository.edit_post(user_id,post_id,audience)
    def like(self,user_id,post_id,enabled): return self.repository.like(user_id,post_id,enabled)
    def comment(self,user_id,post_id,text): return self.repository.comment(user_id,post_id,text)
    def delete_comment(self,user_id,post_id,comment_id): return self.repository.delete_comment(user_id,post_id,comment_id)

    def statistics(self,user_id): return self.repository.stats(user_id)
