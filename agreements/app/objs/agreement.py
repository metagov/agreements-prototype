import logging
import math
import tweepy
from tinydb.database import Document

from .. import core
from . import contract

class Agreement:
    def __init__(self, arg):
        self.agreement_table = core.db.table('agreements')
        self.logger = logging.getLogger(".".join([self.__module__, type(self).__name__]))
        self.balance_limited = False
        self.contract_limited = False
        self.no_members = False
        self.error_parsing = False
        self.valid = True
        
        if type(arg) == int:
            self.id = arg
            if not self.in_database():
                self.logger.warn('Agreement does not exist, unable to generate (status not provided)')
                self.valid = False

        elif type(arg) == tweepy.models.Status:
            status = arg
            self.id = status.id
            self.status = status

        else:
            self.logger.warn('Invalid parameter when creating Agreement')
            self.valid = False

    def get_entry(self):
        return self.agreement_table.get(doc_id=self.id)

    def in_database(self):
        return self.agreement_table.contains(doc_id=self.id)

    # generates a new agreement
    def generate(self, account):
        text = self.status.full_text
        
        state = 'find_command'
        collateral_size = 0
        collateral_type = ''
        # parses command parameters for agreements of type TSC, like, retweet, and none
        for word in text.split():
            if state == 'find_command':
                if word == 'agreement':
                    state = 'find_size'
            
            elif state == 'find_size':
                if word.isnumeric():
                    collateral_size = int(word)
                    collateral_type = 'TSC'
                    state = 'find_type'
                else:
                    collateral_type = 'none'
                    break

            elif state == 'find_type':
                if (word == 'like') or (word == 'likes'):
                    collateral_type = 'like'
                    break
                elif (word == 'retweet') or (word == 'retweets'):
                    collateral_type = 'retweet'
                    break
                else:
                    collateral_type = 'TSC'
                    break
        
        # extracts all users mentioned in tweet
        users = self.status.entities['user_mentions']

        # the first other user becomes the "member" opposite the "creator"
        if len(users) <= 1:
            self.logger.warn('Agreement does not contain other members')
            self.no_members = True
            return False
        else:
            member = users[1]
        
        # attempts to pay with existing balance
        if collateral_type == "TSC":
            if collateral_size > account.check_balance():
                self.logger.warn('Insufficient balance to pay agreement collateral')
                self.balance_limited = True
                return False
            else:
                # removes funds from account balance
                account.change_balance(account.id, -collateral_size)
                self.logger.info(f'Removed {collateral_size} TSC of collateral from the balance of {account.screen_name} [{account.id}]')

        # if user is paying with likes or retweets, the contract will only be created if the agreement is broken
        elif (collateral_type == "like") or (collateral_type == "retweet"):
            self.logger.info(f'Generating new contract for {account.screen_name} [{account.id}] (agreement context)')
                
            status = core.api.get_status(self.id)

            # creates new contract
            con = contract.Contract(status)
            total_value = con.complex_generate(collateral_type, collateral_size)
            
            # contract will not be activated unless the agreement is broken
            con.contract_table.update(
                {'state': 'dead'},
                doc_ids=[self.id]
            )

            if con.resized or con.oversized:
                self.logger.warn('Contract limit reached when creating agreement')
                self.contract_limited = True
                return False

        entry = {
            "state": "open",
            "creator_id": str(account.id),
            "creator_screen_name": account.screen_name,
            "creator_ruling": "",
            "member_id": member['id_str'],
            "member_screen_name": member['screen_name'],
            "member_ruling": "",
            "collateral_type": collateral_type,
            "collateral": str(collateral_size),
            "created": str(self.status.created_at),
            "text": text
        }

        # adding agreement to db
        self.agreement_table.insert(Document(
            entry, doc_id=self.id
        ))

        # updating number of agreements
        def increment_num_agreements(doc):
            num_agreements = int(doc['num_agreements'])
            num_agreements += 1
            doc['num_agreements'] = str(num_agreements)
        self.agreement_table.update(
            increment_num_agreements, 
            doc_ids=[0]
        )

        self.logger.info(entry)
        

    # adds a ruling vote to the agreement from the member or creator
    def vote(self, account, ruling):
        entry = self.get_entry()

        # adds ruling if member
        if str(account.id) == entry['member_id']:
            self.agreement_table.update(
                {'member_ruling': ruling},
                doc_ids=[self.id]
            )
            self.logger.info(f'Member {account.screen_name} [{account.id}] voted {ruling} on Agreement #{self.id}')

        # adds ruling if creator
        elif str(account.id) == entry['creator_id']:
            self.agreement_table.update(
                {'creator_ruling': ruling},
                doc_ids=[self.id]
            )
            self.logger.info(f'Creator {account.screen_name} [{account.id}] voted {ruling} on Agreement #{self.id}')

        # extracting from db
        collateral_type = entry['collateral_type']
        collateral = int(entry['collateral'])
        member_id = int(entry['member_id'])
        member_screen_name = entry['member_screen_name']
        creator_id = int(entry['creator_id'])
        creator_screen_name = entry['creator_screen_name']

        # checks the current ruling state of the agreement
        ruling = self.check_ruling()

        # both users say the agreement was upheld
        if ruling == 'upheld':
            # if the creator used TSC as collateral, it is returned to their balance
            if collateral_type == 'TSC':
                account.change_balance(creator_id, collateral)
                self.logger.info(f'Paid back {collateral} TSC to {creator_screen_name} [{creator_id}] ')

                update_message = f'Agreement is upheld, {collateral} TSC has been repaid to @{creator_screen_name}.'
            
            # if the creator used likes/retweets as collateral nothing happens and the contracts aren't generated
            elif (collateral_type == "like") or (collateral_type == "retweet"):
                self.logger.info('Agreement is upheld, collateral type is future contract, nothing to do')
                # effectively zeroes out dead contract
                core.db.table('contracts').update(
                    {'count': '0'},
                    doc_ids=[self.id]
                )
                
                update_message = f'Agreement is upheld, no contracts will be generated.'
            
            elif collateral_type == "none":
                self.logger.info('Agreement is upheld, collateral type is none, nothing to do')

                update_message = 'Agreement is upheld.'

        # both users say the agreement was broken
        elif ruling == 'broken':
            # if the creator used TSC as collateral, it is transferred to the member
            if collateral_type == 'TSC':
                account.change_balance(member_id, collateral)
                self.logger.info(f'Transferred {collateral} TSC to {member_id} [{member_id}]')
                update_message = f'Agreement is broken, {collateral} TSC has been paid to @{member_screen_name}'
            
            # if the creator used likes/retweets as collateral, a contract is generated and the profit is transferred to the member
            elif (collateral_type == "like") or (collateral_type == "retweet"):
                # retrieving inactive contract
                c_entry = core.db.table('contracts').get(doc_id=self.id)
                c_total = int(c_entry['count'])
                c_value = int(c_entry['price'])
                total_value = c_total * c_value

                # paying tax to agreement engine
                to_pay_engine = math.ceil(total_value * core.Consts.tax_rate)
                collateral = total_value - to_pay_engine

                core.db.table('contracts').update(
                    {'state': 'alive'},
                    doc_ids=[self.id]
                )    
                self.logger.info(f'Collateral contract #{self.id} activated')

                core.db.table('accounts').update(
                    lambda d: d['contracts'].append(str(self.id)),
                    doc_ids=[creator_id]
                )

                # paid out to agreement engine
                account.change_balance(core.engine_id, to_pay_engine)
                account.change_balance(member_id, collateral)
                self.logger.info(f'Transferred {collateral} TSC to {member_screen_name} [{member_id}]') 
                update_message = f'Agreement is broken, @{creator_screen_name}\'s contract was generated and {collateral} TSC has been paid to @{member_screen_name}.'
            
            elif collateral_type == "none":
                self.logger.info('Agreement is broken, collateral type is none, nothing to do.')
                
        elif ruling == 'disputed':
            update_message = f'Agreement outcome is disputed. No action will be taken, users can change their ruling to come to a consensus.'

        if (ruling == 'upheld') or (ruling == 'broken') or (ruling == 'disputed'):
            # send result
            core.emit(update_message, self.id)
    
    def check_ruling(self):
        m_ruling = self.get_entry()['member_ruling']
        c_ruling = self.get_entry()['creator_ruling']

        if m_ruling and c_ruling:
            if m_ruling == c_ruling:
                self.logger.info(f'Consensus reached: {c_ruling}')

                self.agreement_table.update(
                    {'state': 'closed'},
                    doc_ids=[self.id]
                )

                return c_ruling
            else:
                self.logger.info('Dispute in agreement')
                return 'disputed'
        else:
            self.logger.info('Have not received all rulings')
            return 'waiting'