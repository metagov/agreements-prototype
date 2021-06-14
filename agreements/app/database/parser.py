from tinydb.database import Document

from .metadata import Metadata
from ..objs import account, contract
from ..core import Consts

class Parser:
    def __init__(self, db, api):
        self.db = db
        self.api = api
        self.meta = Metadata(db)
        self.accounts = db.table('accounts')
        self.contracts = db.table('contracts')
        self.executions = db.table('executions')
        self.agreements = db.table('agreements')
        self.statuses = db.table('statuses')
        self.me = api.me()

        # intializing accounts table
        if not self.accounts.contains(doc_id=0):
            self.accounts.insert(Document(
                {
                    'num_accounts': '0'
                },
                doc_id=0))
            
            account.Account(self.me)
        
        # intializing contracts table
        if not self.contracts.contains(doc_id=0):
            self.contracts.insert(Document(
                {
                    'num_contracts': '0',
                    # 'total_value': '0',
                },
                doc_id=0))
        
        if not self.executions.contains(doc_id=0):
            self.executions.insert(Document(
                {
                    'num_executions': '0',
                },
                doc_id=0))
        
        if not self.agreements.contains(doc_id=0):
            self.agreements.insert(Document(
                {
                    'num_agreements': '0'
                },
                doc_id=0))
    
    def parse(self, status):
        # decides what command a tweet is and runs the proper code
        self.add_status(status)
        text = status.full_text

        acc = account.Account(status.user)

        # finds first keyword
        kword = None
        for word in text.split():
            if word in Consts.kwords.values():
                kword = word
                break

        # calls function based on first keyword found
        if kword == Consts.kwords['gen']:
            acc.create_contract(status)
        elif kword ==  Consts.kwords['exe']:
            acc.execute_contracts(status)
        elif kword == Consts.kwords['bal']:
            acc.send_current_balance(status)
        elif kword == Consts.kwords['rep']:
            acc.send_current_reputation(status)
        elif kword == Consts.kwords['lik']:
            acc.send_current_likes(status)
        elif kword == Consts.kwords['rtw']:
            acc.send_current_retweets(status)
        elif kword == Consts.kwords['snd']:
            acc.send_tsc(status)
        elif kword == Consts.kwords['agr']:
            acc.create_agreement(status)
        elif kword == Consts.kwords['uph']:
            acc.vote_upheld(status)
        elif kword == Consts.kwords['brk']:
            acc.vote_broken(status)

    # adds data from every mention status to the database 
    def add_status(self, status):
        if self.statuses.contains(doc_id=status.id):
            return False

        dict_status = {
            'text': status.full_text,
            'user_full_name': status.user.name,
            'user_screen_name': status.user.screen_name,
            'user_id': str(status.user.id),
            'created': str(status.created_at),
            'parent_id': str(status.in_reply_to_status_id) if status.in_reply_to_status_id else None,
        }

        # adding status to database
        self.statuses.insert(Document(
            dict_status, 
            doc_id=status.id
        ))

        return True