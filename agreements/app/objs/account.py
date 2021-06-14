import logging
import math
import tweepy
from tinydb.database import Document

from .. import core
from . import contract, agreement

# represents a single account
class Account:
    def __init__(self, arg):
        self.account_table = core.db.table('accounts')
        self.logger = logging.getLogger(".".join([self.__module__, type(self).__name__]))

        new_user = False

        # can be initialized with a user id integer, attempts to find account entry in db
        if type(arg) == int:
            self.id = arg
            if not self.in_database():
                self.logger.warn('Account does not exist, unable to generate (user object not provided)')
                return

        # can be initialized with a tweepy user object, generates new db entry if doesn't already exist
        elif type(arg) == tweepy.models.User:
            user = arg
            self.id = user.id
            if not self.in_database():
                self.generate(user)
                new_user = True
                
        else:
            self.logger.warn('Invalid parameter when creating Account')

        self.screen_name = self.get_entry()['screen_name']

        # greeting message for new users (excluding the agreement engine)
        if new_user and (self.id != core.api.me().id):
            self.logger.info(f"Welcoming {self.screen_name}")
            message = f"@{self.screen_name} Welcome to Agreement Engine! Check out https://agreements.metagov.org/about and https://agreements.metagov.org/help to learn about agreements and how to make them!"
            core.emit(message)

    # returns dict from db
    def get_entry(self):
        return self.account_table.get(doc_id=self.id)

    # checks if user id is already in db
    def in_database(self):
        return self.account_table.contains(doc_id=self.id)
    
    # generates a new account
    def generate(self, user):
        # initializing default account data
        entry = {
            'full_name': user.name,
            'screen_name': user.screen_name,
            'reputation': '0',
            'balance': '0',
            'contracts': [],
            'likes': [],
            'retweets': []
        }

        # inserting account data into table
        self.account_table.insert(Document(
            entry, 
            doc_id=self.id
        ))

        # updating number of accounts
        def increment_num_accounts(doc):
            num_accounts = int(doc['num_accounts'])
            num_accounts += 1
            doc['num_accounts'] = str(num_accounts)
        self.account_table.update(
            increment_num_accounts, 
            doc_ids=[0]
        )

        self.logger.info(f'New account created for @{user.screen_name}!')
    
    # modifies account balance
    def change_balance(self, user_id, amount):
        # passed into tiny db update function, adds to balance
        def add_to_balance(doc):
            doc['balance'] = str(int(doc['balance']) + amount)
        
        # updates account balance
        self.account_table.update(
            add_to_balance,
            doc_ids=[user_id]
        )        
    
    def check_balance(self):
        return int(self.account_table.get(doc_id=self.id)['balance'])
    
    def check_reputation(self):
        return int(self.account_table.get(doc_id=self.id)['reputation'])
    
    def adjust_reputation(self, change):
        # updating reputation
        def update_rep(doc):
            new_rep = self.check_reputation() + change
            # keeps reputation with bounds of min/max value
            new_rep = min(new_rep, core.Consts.max_reputation)
            new_rep = max(new_rep, core.Consts.min_reputation)

            doc['reputation'] = str(new_rep)
        self.account_table.update(
            update_rep,
            doc_ids=[self.id]
        )

    def send_current_balance(self, status):
        self.logger.info('Sending current balance')

        message = f'@{self.screen_name} You currently have {self.check_balance()} TSC in your account.'
        core.emit(message, status.id)
    
    def send_current_reputation(self, status):
        self.logger.info('Sending current reputation')

        message = f'@{self.screen_name} You currently have a reputation of {self.check_reputation()}.'
        core.emit(message, status.id)
        
    def send_current_likes(self, status):
        likes = contract.Pool().count_user_contracts('like', self.id)

        self.logger.info('Sending active like contract count')

        message = f'@{self.screen_name} You currently have {likes} active like contracts.'
        core.emit(message, status.id)

    def send_current_retweets(self, status):
        retweets = contract.Pool().count_user_contracts('retweet', self.id)

        self.logger.info('Sending active retweet contract count')

        message = f'@{self.screen_name} You currently have {retweets} active retweet contracts.'
        core.emit(message, status.id)

    # checks whether a user has had a like contract called in on a status
    def has_liked(self, status_id):
        likes = self.get_entry()['likes']
        return str(status_id) in likes
    
    # checks whether a user has had a retweet contract called in on a status
    def has_retweeted(self, status_id):
        retweets = self.get_entry()['retweets']
        return str(status_id) in retweets

    def create_agreement(self, status):
        self.logger.info(f'Generating new agreement for {self.screen_name} [{self.id}]')

        new_agreement = agreement.Agreement(status)
        new_agreement.generate(self)

        if new_agreement.contract_limited:
            update_message = f'This agreement could not be created because you have reached your contract limit.'
        elif new_agreement.balance_limited:
            update_message = f'This agreement could not be created because you have exceeded your balance.'
        elif new_agreement.no_members:
            update_message = f'Agreements must contain another member.'
        elif new_agreement.error_parsing:
            return False
            # not sending messages for invalid commands at the moment, could get annoying
        else:
            a_entry = new_agreement.get_entry()
            if not a_entry:
                self.logger.warn("Couldn't get agreement from database (this shouldn't happen)")
                return False
            collateral = a_entry['collateral']
            c_type = a_entry['collateral_type']

            if c_type == 'TSC':
                update_message = f'Your agreement staking {collateral} TSC has been created!'
            elif c_type == 'none':
                update_message = f'Your unenforced agreement has been created!'
            else:
                update_message = f'Your agreement staking {collateral} {c_type}s has been created!'

        message = f'@{self.screen_name} ' + update_message
        core.emit(message, status.id)

    def vote_upheld(self, status):
        original_agreement = agreement.Agreement(status.in_reply_to_status_id)

        if original_agreement.valid:
            original_agreement.vote(self, 'upheld')
        else:
            self.logger.warn("Invalid agreement id, entry not found")
    
    def vote_broken(self, status):
        original_agreement = agreement.Agreement(status.in_reply_to_status_id)

        if original_agreement.valid:
            original_agreement.vote(self, 'broken')
        else:
            self.logger.warn("Invalid agreement id, entry not found")

    # generates a new contract
    def create_contract(self, status):
        self.logger.info(f'Generating new contract for {self.screen_name} [{self.id}]')

        # created contract object
        new_contract = contract.Contract(status)
        total_value = new_contract.generate()

        if total_value == False:
            self.logger.warn('Exiting invalid contract')
        
        else:
            # calculates taxed amount and amount to pay users based on total value of contract
            to_pay_engine = math.ceil(total_value * core.Consts.tax_rate)
            to_pay_user = total_value - to_pay_engine

            # paid out to user and agreement engine
            self.change_balance(core.engine_id, to_pay_engine)
            self.change_balance(self.id, to_pay_user)
            self.logger.info(f'Paid {self.screen_name} [{self.id}] {to_pay_user} TSC ({to_pay_engine} withheld)')

            # adds contract id to account list
            self.account_table.update(
                lambda d: d['contracts'].append(str(status.id)),
                doc_ids=[self.id]
            )

        # generating message to send to user
        c_entry = new_contract.get_entry()
        update_message = ''
        
        if new_contract.bad_args:
            return False

        if new_contract.oversized:
            update_message = f'You have reached your contract limit and cannot generate new ones until they have been used up.'
        elif new_contract.resized:
            update_message = f'Your request exceeded your {c_entry["type"]} contract limit so it was resized. Your account has been credited {to_pay_user} TSC for this {c_entry["count"]} {c_entry["type"]} contract.'
        elif new_contract.no_followers:
            update_message = f'Your account has 0 followers, so contracts cannot be generated.'
        else:
            update_message = f'Successfully generated! Your account has been credited {to_pay_user} TSC for this {c_entry["count"]} {c_entry["type"]} contract.'

        message = f'@{self.screen_name} ' + update_message
        core.emit(message, status.id)

    # executes contracts on a requested post for a certain amount of TSC
    def execute_contracts(self, status):
        self.logger.info(f'Executing contracts for {self.screen_name} [{self.id}]')

        text = status.full_text 
        arg = text[text.find(core.Consts.kwords['exe']):].split()[1]

        # extracting amount to spend
        try:
            to_spend = int(arg)
        except ValueError:
            self.logger.warn(f'Could not parse to_spend: "{arg}"')
            return False
        
        # executed on the post being replied to (ie reply to post you want to execute contracts on)
        executing_on = status.in_reply_to_status_id

        self.logger.info(f'New execution request spending {to_spend} TSC on status #{executing_on}')

        if to_spend > self.check_balance():
            self.logger.info(f'Execution request exceeds balance')

            update_message = f'This request exceeds your balance of {self.check_balance()} TSC.'
        else:
            contract_pool = contract.Pool()
            # auto execute function will try to spend all of the funds requested executing contracts
            executed_count, amount_spent = contract_pool.auto_execute_contracts(self.id, executing_on, to_spend)

            # updates balance based on amount actually spent
            self.change_balance(self.id, -amount_spent)

            if executed_count > 0:
                update_message = f'Executed {executed_count} contracts for {amount_spent} TSC.'
            else:
                update_message = f'Unable to execute any contracts, your account has not been charged.'

        message = f'@{self.screen_name} ' + update_message
        core.emit(message, status.id)

    def send_tsc(self, status):
        self.logger.info(f'Sending TSC from {self.screen_name} [{self.id}]')

        text = status.full_text
        arg = text[text.find(core.Consts.kwords['snd']):].split()[1]

        try:
            payment = int(arg)
        except ValueError:
            self.logger.warn(f'Could not parse payment: "{arg}"')
            return False

        users = status.entities['user_mentions']

        # sending to which user?
        if len(users) <= 1:
            self.logger.warn('Did not specify users to send to')
            return False

        recipient_id = users[1]['id']
        recipient_user = core.api.get_user(recipient_id)

        # balance check
        if payment > self.check_balance():
            self.logger.warn('Insufficient balance to send')
            update_message = 'Insufficient balance to send that amount.'
        else:
            # removing from own balance
            self.change_balance(self.id, -payment)
            # adding to recipient's balance
            recipient = Account(recipient_user)
            self.change_balance(recipient.id, payment)
            self.logger.info(f'Transferred {payment} from @{self.screen_name} to @{recipient.screen_name}')

            update_message = f'Sent {payment} TSC to @{recipient.screen_name}.'
        
        message = f'@{self.screen_name} ' + update_message
        core.emit(message, status.id)
