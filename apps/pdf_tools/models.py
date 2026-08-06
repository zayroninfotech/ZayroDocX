import uuid
from django.db import models


# ── ConnectSpace ─────────────────────────────────────────────────────────────

class CSRoom(models.Model):
    code    = models.CharField(max_length=6, unique=True, db_index=True)
    created = models.DateTimeField(auto_now_add=True)

    def peer_count(self):
        return self.peers.count()

    def __str__(self):
        return self.code


class CSPeer(models.Model):
    room    = models.ForeignKey(CSRoom, on_delete=models.CASCADE, related_name='peers')
    peer_id = models.CharField(max_length=8)


class CSFile(models.Model):
    room      = models.ForeignKey(CSRoom, on_delete=models.CASCADE, related_name='files')
    file_id   = models.CharField(max_length=36, default=uuid.uuid4, db_index=True)
    name      = models.CharField(max_length=255)
    size      = models.BigIntegerField()
    file_path = models.CharField(max_length=500)   # absolute path to temp file
    from_peer = models.CharField(max_length=8)
    ts        = models.FloatField()
