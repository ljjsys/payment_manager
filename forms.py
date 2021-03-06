# coding=utf-8
from datetime import datetime
from flask_wtf import Form
from wtforms_alchemy import model_form_factory
from wtforms import (
    PasswordField, TextField, SelectField, DateField, TextAreaField,
    DecimalField)
from wtforms.validators import (
    Required, EqualTo, Regexp, NumberRange, Optional)
from models import db
from models import (
    User, Role, Address, Person, Standard, PersonStandardAssoc, Bankcard,
    Note, PayBookItem, PayBook)


BaseModelForm = model_form_factory(Form)


class ModelForm(BaseModelForm):
    @classmethod
    def get_session(cls):
        return db.session


class PeroidForm(Form):
    start_date = DateField(unicode('start date'))
    end_date = DateField(unicode('end date'))


class DateForm(Form):
    date = DateField(unicode('date'), validators=[Required()])


class LoginForm(Form):
    name = TextField('name', validators=[Required()])
    password = PasswordField('password', validators=[Required()])


class ChangePasswordForm(Form):
    oldpassword = PasswordField(u'old password', validators=[Required()])
    newpassword = PasswordField(u'new password', validators=[Required()])
    confirm = PasswordField(
        u'confirm password', validators=[EqualTo('newpassword')])

    def populate_obj(self, user, name=None):
        if name:
            user.name = name
        user.password = self.newpassword.data
        return user


class UserForm(ModelForm):
    class Meta:
        model = User
    password = PasswordField('password', validators=[Required()])


class _AdminRoleForm(Form):
    role = SelectField('role add/remove for user', coerce=int)

    def __init__(self, user, **kwargs):
        if user is None or not isinstance(user, User):
            raise ValueError("user can't be None and must a User instance")
        kwargs.update({'obj': user})
        super(_AdminRoleForm, self).__init__(**kwargs)


class AdminAddRoleForm(_AdminRoleForm):

    def __init__(self, user, **kwargs):
        super(AdminAddRoleForm, self).__init__(user, **kwargs)
        if user.roles:
            self.role.choices = map(
                lambda x: (x.id, x.name),
                Role.query.filter(
                    ~Role.id.in_(map(lambda x: x.id, user.roles))).all())
        else:
            self.role.choices = map(
                lambda x: (x.id, x.name), Role.query.all())

    def populate_obj(self, user):
        role = Role.query.get(self.role.data)
        user.roles.append(role)


class AdminUserBindaddrForm(Form):
    address = SelectField(
        'address',
        validators=[Optional()],
        coerce=lambda x: x and int(x))

    def __init__(self, *args, **kwargs):
        super(AdminUserBindaddrForm, self).__init__(*args, **kwargs)
        self.address.choices = map(
            lambda addr: (addr.id, addr.name),
            Address.query.all())
        self.address.choices.append(('', ''))


class AdminRemoveRoleForm(_AdminRoleForm):
    def __init__(self, user, **kwargs):
        super(AdminRemoveRoleForm, self).__init__(user, **kwargs)
        if user.roles:
            self.role.choices = map(lambda x: (x.id, x.name), user.roles)
        else:
            self.role.choices = [(None, '')]

    def populate_obj(self, user):
        if self.role.data > 0:
            role = Role.query.get(self.role.data)
            user.roles.remove(role)


class RoleForm(ModelForm):
    class Meta:
        model = Role


class AddressForm(ModelForm):
    parent_id = SelectField(
        unicode('parent id'),
        validators=[Optional()],
        coerce=lambda x: x and int(x),
        default=None)

    def __init__(self, **kwargs):
        super(AddressForm, self).__init__(**kwargs)
        address = kwargs.get('obj', None)
        if address:
            # self can not be self's parent
            query = Address.query.filter(Address.id != address.id)
        else:
            query = Address.query
        self.parent_id.choices = map(lambda x: (x.id, x.name), query.all())
        self.parent_id.choices.append(('', ''))

    class Meta:
        model = Address


class PersonForm(ModelForm):
    address_id = SelectField(
        'address', validators=[Required()], coerce=int)
    birthday = DateField('birthday', validators=[Required()])
    personal_wage = DecimalField(
        'personal wage', validators=[NumberRange(min=0.00, max=10000)],
        places=7, rounding=2)

    def __init__(self, user, **kwargs):
        super(PersonForm, self).__init__(**kwargs)
        self.user = user
        if user.address:
            addresses = [a for a in user.address.descendants]
            addresses.append(user.address)
        else:
            addresses = []
        self.address_id.choices = map(lambda x: (x.id, x.name), addresses)

    def populate_obj(self, person):
        super(PersonForm, self).populate_obj(person)
        person.create_by = self.user
        if person.status is None:
            person.reg()

    class Meta:
        model = Person
        only = ['idcard', 'name',  'address_detail', 'securi_no']


class StandardForm(ModelForm):

    class Meta:
        model = Standard


class StandardBindForm(Form):

    standard_id = SelectField(
        'standard', validators=[Required()], coerce=int)
    start_date = DateField('start date', validators=[Required()])
    end_date = DateField('end date')

    def __init__(self, person, **kwargs):
        super(StandardBindForm, self).__init__(**kwargs)
        self.person = person
        self.standard_id.choices = map(lambda s: (s.id, s.name),
                                       Standard.query.all())

    def populate_obj(self, person):
        assoc = PersonStandardAssoc(
            person=self.person,
            standard_id=self.standard_id.data,
            start_date=self.start_date.data,
            end_date=self.end_date.data
        )
        db.session.add(assoc)


class BankcardForm(ModelForm):

    class Meta:
        model = Bankcard
        only = ['no', 'name']


class BankcardBindForm(Form):
    idcard = TextField('idcard',
                       validators=[Required(), Regexp(r'\d{17}[\d|X]')])


class NoteForm(ModelForm):
    content = TextAreaField('content', validators=[Required()])
    end_date = DateField('end date')

    class Meta:
        model = Note
        only = ['start_date']


class PayItemForm(ModelForm):
    parent_id = SelectField(
        'parent', validators=[Optional()], coerce=int)

    def __init__(self, *args, **kwargs):
        super(PayItemForm, self).__init__(*args, **kwargs)
        query = PayBookItem.query
        obj = kwargs.get('obj', None)
        if obj:
            query = query.filter(PayBookItem.id != obj.id)
        self.parent_id.choices = map(lambda a: (a.id, a.name), query.all())

    class Meta:
        model = PayBookItem


class AmendForm(ModelForm):
    bankcard = TextField('bankcard', validators=[Regexp(
        r'^(?:\d{19})|(?:\d{2}-\d{15})$')])
    money = DecimalField(
        'money',
        validators=[Required(), NumberRange(min=0.01, max=1000000)],
        places=7, rounding=2)

    def __init__(self, **kwargs):
        super(AmendForm, self).__init__(**kwargs)
        self.bookmanager = kwargs['obj']
        self.books = self.bookmanager.lst_groupby_bankcard()

    def validate_on_submit(self):
        for book in self.books:
            item = (lambda x, q: isinstance(x, int) and q.get(x) or x)(
                book.item, PayBookItem.query)
            if item.name not in ['sys_should_pay', 'bank_payed']:
                return False
            bankcard = (lambda x, q: isinstance(x, int) and q.get(x) or x)(
                book.bankcard, Bankcard.query)
            if not bankcard.binded:
                return False
        return super(AmendForm, self).validate_on_submit()

    def populate_obj(self, lst=[]):
        sys_should, sys_amend, bank_should = map(
            lambda name: PayBookItem.query.filter(
                PayBookItem.name == name).one(),
            ('sys_should_pay', 'sys_amend', 'bank_should_pay'))
        bankcard = Bankcard.query.filter(
            Bankcard.no == self.bankcard.data).one()
        if self.books:
            # valish all money of all bankcards witch belong person
            lst.extend(reduce(
                lambda x, y: x.extend(self.bookmanager.create_tuple(
                    y.bankcard_id, y.bankcard_id, sys_should, bank_should,
                    y.money, remark='remend', commit=False)) or x,
                self.books, []))
            # amend money to new bankcard
            lst.extend(
                self.bookmanager.create_tuple(
                    bankcard, bankcard, sys_amend, bank_should,
                    self.money.data, remark='remnd', commit=False))


class BatchSuccessFrom(Form):
    peroid = DateField('peroid', validators=[Required()])
    fails = TextAreaField('falied bankcard', validators=[
        Regexp(r'(?:(?:\d{19}|(?:\d{2}-\d{15})),\d+(?:\.\d+)?[\r\n]?)*')])


class FailCorrectForm(Form):
    bankcard = TextField(
        'bankcard', validators=[Regexp('^(?:\d{19})|(?:{\d{2}-\d{15})$')])


class SuccessCorrectForm(Form):
    money = DecimalField('failed money',
                         validators=[NumberRange(0.01, 1000000)],
                         places=7, rounding=2)
