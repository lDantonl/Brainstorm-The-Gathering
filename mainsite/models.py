from django.db import models
import re
from datetime import datetime, tzinfo, timedelta
import unicodedata
from django.contrib.auth.models import User
from django.db import models
from haystack import signals

class EST(tzinfo):

    def utcoffset(self, dt):
        return timedelta(hours=-5)

    def tzname(self, dt):
        return 'EST'

    def dst(self, dt):
        return timedelta(0)

class FavoriteCard(models.Model):
    card = models.ForeignKey('mainsite.Card')
    user = models.OneToOneField(User)

class Card(models.Model):
    name = models.CharField(max_length=200)
    color = models.CharField(max_length=200)
    manacost = models.CharField(max_length=200, null=True)
    rules = models.TextField(null=True)
    power = models.CharField(max_length=200, null=True)
    toughness = models.CharField(max_length=200, null=True)
    sets = models.ManyToManyField('mainsite.Set')
    typing = models.ManyToManyField('mainsite.Typing')
    sub_typing = models.ManyToManyField('mainsite.SubTyping')
    super_typing = models.ManyToManyField('mainsite.SuperTyping')
    cmc = models.IntegerField()

    class Meta:
        ordering = ['name']

    def __unicode__(self):
        return self.name

    def get_image_url(self, set_name=None):
        if set_name and self.sets.all().filter(name=set_name):
            return "http://static.brainstormtg.com/card_images/%s/%s.jpeg" % (set_name,self.name)
        return "http://static.brainstormtg.com/card_images/%s/%s.jpeg" % (self.sets.all()[0],self.name)

    def get_absolute_url(self):
        return "/info/%s/%s/" % (self.sets.all()[0], self.name)

    def get_absolute_url(self, set_name=None):
        if set_name and self.sets.all().filter(name=set_name):
            return "/info/%s/%s/" % (self.sets.all().get(name=set_name),self.name)
        return "/info/%s/%s/" % (self.sets.all()[0], self.name)

class Format(models.Model):
    name = models.CharField(max_length=200)
    legal_sets = models.ManyToManyField('mainsite.Set')
    banned_cards = models.ManyToManyField('mainsite.Card',related_name='banned_cards')
    restricted_cards = models.ManyToManyField('mainsite.Card',related_name='restricted_cards')

    def __unicode__(self):
        return self.name

    def checkCard(self, card):
        for _set in self.legal_sets.all():
            if card.sets.filter(pk=_set.pk):
                if self.banned_cards.filter(pk=card.pk):
                    return 'Banned'
                if self.restricted_cards.filter(pk=card.pk):
                    return 'Restricted'
                return 'Legal'
        return 'Banned'

    def legal(self, deck):
        numCards = 0
        for card_count in deck.card_counts.all():
            numCards += card_count.multiplicity
            if self.checkCard(card_count.card) == 'Banned':
                return card_count.card.name + ' is banned in ' + self.name
            if self.checkCard(card_count.card) == 'Restricted' and card_count.multiplicity > 1 and not card_count.card.super_typing.filter(name='Basic') and not card_count.card.name == 'Relentless Rats':
                return card_count.card.name + ' is restricted in ' + self.name + ', but there is more than one copy in the maindeck'
            if card_count.multiplicity > 4 and not card_count.card.super_typing.filter(name='Basic') and not card_count.card.name == 'Relentless Rats':
                return 'There are more than 4 copies of ' + card_count.card.name + ' in the deck'
        if numCards < 60:
            return 'There must be at least 60 cards in the main deck'
        if self.name == 'commander' and numCards != 100:
            return 'Commander requires exactly 100 cards in a deck'
        numCards = 0
        for card_count in deck.sb_counts.all():
            numCards += card_count.multiplicity
            if self.checkCard(card_count.card) == 'Banned':
                return card_count.card.name + ' is banned in ' + self.name + ', but there is a copy in the sideboard'
            if self.checkCard(card_count.card) == 'Restricted' and card_count.multiplicity > 1 and not card_count.card.super_typing.filter(name='Basic') and not card_count.card.name == 'Relentless Rats':
                return card_count.card.name + ' is restricted in ' + self.name + ', but there is more than one copy in the sideboard'
            if card_count.multiplicity > 4 and not card_count.card.super_typing.filter(name='Basic') and not card_count.card.name == 'Relentless Rats':
                return 'There are more than 4 copies of ' + card_count.card.name + ' in the sideboard'
            if deck.card_counts.filter(card=card_count.card):
                if deck.card_counts.get(card=card_count.card).multiplicity + card_count.multiplicity > 4 and not card_count.card.super_typing.filter(name='Basic') and not card_count.card.name == 'Relentless Rats':
                    return 'There are more than 4 copies of ' + card_count.card.name + ' between the maindeck and the sideboard'
                if self.checkCard(card_count.card) == 'Restricted' and deck.card_counts.get(card=card_count.card).multiplicity + card_count.multiplicity > 1 and not card_count.card.super_typing.filter(name='Basic') and not card_count.card.name == 'Relentless Rats':
                    return card_count.card.name + ' is restricted in ' + self.name
        if numCards == 0 or numCards == 15:
            return False
        return 'Sideboards need to have exactly 0 or 15 cards'

class Set(models.Model):
    name = models.CharField(max_length=200)
    long_name = models.CharField(max_length=200)

    def __unicode__(self):
        return self.name

class Typing(models.Model):
    name = models.CharField(max_length=200)

    def __unicode__(self):
        return self.name

class SubTyping(models.Model):
    name = models.CharField(max_length=200)

    def __unicode__(self):
        return self.name

class SuperTyping(models.Model):
    name = models.CharField(max_length=200)

    def __unicode__(self):
        return self.name

class CardCount(models.Model):
    card = models.ForeignKey('mainsite.Card')
    multiplicity = models.IntegerField()

    @staticmethod
    def getCardCount(_card,_multiplicity):
        if CardCount.objects.filter(card=_card).filter(multiplicity=_multiplicity).count() == 0:
            newCount = CardCount(card=_card,multiplicity=_multiplicity)
            newCount.save()
            return newCount
        else:
            return CardCount.objects.filter(card=_card).get(multiplicity=_multiplicity)

class Deck(models.Model):
    name = models.CharField(max_length=200)
    user = models.ForeignKey(User)
    created = models.DateTimeField('datetime.now(EST())')
    description = models.TextField()
    card_counts = models.ManyToManyField('mainsite.CardCount',related_name='md')
    sb_counts = models.ManyToManyField('mainsite.CardCount',related_name='sb')

    def __unicode__(self):
        return self.name

    def publish(self):
        publishedDeck = PublishedDeck(legacy_legal=not self.format_check(Format.objects.get(name=legacy)),vintage_legal=not self.format_check(Format.objects.get(name=vintage)),modern_legal=not self.format_check(Format.objects.get(name=modern)),standard_legal=not self.format_check(Format.objects.get(name=standard)),commander_legal=not self.format_check(Format.objects.get(name=commander)),score=0,user=self.user,published=datetime.now(EST()),description=self.description,card_counts=self.card_counts.objects.all(),sb_counts=self.sb_counts.objects.all())
        publishedDeck.save()
        breakdown = Card_Breakdown()
        breakdown.initialize(publishedDeck)
        breakdown.save()
        return publishedDeck

    def addCard(self, str):  #argument is the name of the card to add
        self.setNumCard(str=str,num=1)
        '''if(self.card_counts.filter(card=Card.objects.get(name=str)).count() != 0):
            num = self.card_counts.get(card=Card.objects.get(name=str)).multiplicity
            self.card_counts.remove(self.card_counts.get(card=Card.objects.get(name=str)))
            self.card_counts.add(CardCount.getCardCount(Card.objects.get(name=str),num+1))
        else:
            self.card_counts.add(CardCount.getCardCount(Card.objects.get(name=str),1))'''

    def removeCard(self, str): #argument is the name of the card to add
        if(self.card_counts.filter(card=Card.objects.get(name=str)).count() != 0):
            self.card_counts.get(card=Card.objects.get(name=str)).delete()

    def setNumCard(self, str, num):
        self.removeCard(str)
        if num > 0:
            cardCount, created = CardCount.objects.get_or_create(card=Card.objects.get(name=str),multiplicity=num)
            self.card_counts.add(cardCount)
            '''if(self.card_counts.filter(card=Card.objects.get(name=str)).count() == 0):
                if (CardCount.objects.filter(card=Card.objects.get(name=str)).filter(multiplicity=num).count() == 0):
                    card = CardCount(card=Card.objects.get(name=str),multiplicity=num)
                    card.save()
                    self.card_counts.add(card)
                else:
                    self.card_counts.add(CardCount.objects.filter(card=Card.objects.get(name=str)).get(multiplicity=num))
            else:
                card = self.card_counts.get(card=Card.objects.get(name=str))
                card.multiplicity = num'''

    def getMultiplicity(self, str):
        return int(self.card_counts.filter(card=Card.objects.get(name=str)).count())

    def format_check(self, format): #returns true if the calling deck is legal in format
        for _card_count in card_counts:
            if _card_count.card in format.banned_cards:
                return False
            if _card_count.card in format.restricted_cards and _card_count.multiplicity > 1:
                return False
            legal_sets = False
            for _set in _card_count.card.sets:
                if _set in format.legal_sets:
                    legal_sets = True
            if not legal_sets:
                return False
        return True

class PublishedDeck(models.Model):
    name = models.CharField(max_length=200)
    score = models.IntegerField()
    user = models.ForeignKey(User)
    published = models.DateTimeField()
    description = models.TextField()
    card_counts = models.ManyToManyField('mainsite.CardCount',related_name='mdPub')
    sb_counts = models.ManyToManyField('mainsite.CardCount',related_name='sbPub')
    legacy_legal = models.BooleanField()
    vintage_legal = models.BooleanField()
    modern_legal = models.BooleanField()
    standard_legal = models.BooleanField()
    commander_legal = models.BooleanField()
    comments = models.ManyToManyField('mainsite.Comment')

    def __unicode__(self):
        return self.name

    def pull_deck(self, newUser):
        ownedDeck = Deck(user=newUser,created=datetime.now(EST()),description=self.description,card_counts=self.card_counts.objects.all())
        ownedDeck.save()
        return ownedDeck

    def increment_score(self):
        self.score = self.score + 1
        self.save()
        return self.score

    def decrement_score(self):
        self.score = self.score - 1
        self.save()
        return self.score

class Collection(models.Model):
    user = models.ForeignKey(User, primary_key=True)
    card_counts = models.ManyToManyField('mainsite.CardCount')

    def getMultiplicity(self, str):
        return int(self.card_counts.filter(card=Card.objects.get(name=str)).count())

    def addCard(self, str):  #argument is the name of the card to add
        if(self.card_counts.filter(card=Card.objects.get(name=str)).count() == 0):
            if (CardCount.objects.filter(card=Card.objects.get(name=str)).filter(multiplicity=1).count() == 0):
                card = CardCount(card=Card.objects.get(name=str),multiplicity=1)
                card.save()
                self.card_counts.add(card)
            else:
                self.card_counts.add(CardCount.objects.filter(card=Card.objects.get(name=str)).get(multiplicity=1))
        else:
            card = self.card_counts.get(card=Card.objects.get(name=str))
            card.multiplicity = card.multiplicity + 1

    def removeCard(self, str): #argument is the name of the card to add
        if(self.card_counts.filter(card=Card.objects.get(name=str)).count() != 0):
            self.card_counts.get(card=Card.objects.get(name=str)).delete()

    def setNumCard(self, str, num):
        if (num <= 0):
            if(self.card_counts.filter(card=Card.objects.get(name=str)).count() != 0):
                self.card_counts.get(card=Card.objects.get(name=str)).delete()
        else:
            if(self.card_counts.filter(card=Card.objects.get(name=str)).count() == 0):
                if (CardCount.objects.filter(card=Card.objects.get(name=str)).filter(multiplicity=num).count() == 0):
                    card = CardCount(card=Card.objects.get(name=str),multiplicity=num)
                    card.save()
                    self.card_counts.add(card)
                else:
                    self.card_counts.add(CardCount.objects.filter(card=Card.objects.get(name=str)).get(multiplicity=num))
            else:
                card = self.card_counts.get(card=Card.objects.get(name=str))
                card.multiplicity = num

class Comment(models.Model):
    user = models.ForeignKey(User)
    published_deck = models.ForeignKey('mainsite.PublishedDeck')
    timestamp = models.DateTimeField()
    message = models.TextField()

class Card_Breakdown(models.Model):
    #number of cards
    number_of_cards = models.IntegerField(default=0)
    #mana count
    
    #COLORS ARE BASED OFF A STRING
    red_mana = models.IntegerField(default=0)
    blue_mana = models.IntegerField(default=0)
    green_mana = models.IntegerField(default=0)
    black_mana = models.IntegerField(default=0)
    white_mana = models.IntegerField(default=0)
    colorless_mana = models.IntegerField(default=0)

    red = models.IntegerField(default=0)
    blue = models.IntegerField(default=0)
    green = models.IntegerField(default=0)
    black = models.IntegerField(default=0)
    white = models.IntegerField(default=0)
    colorless = models.IntegerField(default=0)


    #card count types
    creature_count = models.IntegerField(default=0)
    land_count = models.IntegerField(default=0)
    sorcery_count = models.IntegerField(default=0)
    instant_count = models.IntegerField(default=0)
    enchantment_count = models.IntegerField(default=0)
    artifact_count = models.IntegerField(default=0)
    planeswalker_count = models.IntegerField(default=0)

    #MAPPING FOR MANA_CURVE
    mana_curve = models.CommaSeparatedIntegerField(max_length=500, default='0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0')

    deck = models.CharField(max_length=500,default='')
    #Sub_decks to add
    
    def __unicode__(self):
        return self.deck.name

    def initialize(self, deck):
        super(Card_Breakdown,self).__init__()
        self.number_of_cards=0
        self.red_mana = 0
        self.blue_mana = 0
        self.green_mana = 0
        self.black_mana = 0
        self.white_mana = 0
        self.colorless_mana = 0

        self.red = 0
        self.blue = 0
        self.green = 0
        self.black = 0
        self.white = 0
        self.colorless = 0

        tempWhite = 0
        tempBlue = 0
        tempBlack = 0
        tempRed = 0
        tempGreen = 0

        self.creature_count = 0
        self.land_count = 0
        self.sorcery_count = 0
        self.instant_count = 0
        self.enchantment_count = 0
        self.artifact_count = 0
        self.planeswalker_count = 0
        curve=[0 for index in xrange(19)]
        for x in deck.card_counts.all():
            curve[x.card.cmc%20] += x.multiplicity
            if x.card.manacost:
                normal=unicodedata.normalize('NFKD', x.card.manacost).encode('ascii','ignore')
            else:
                normal=''
            #determines the color of the card
            if x.card.manacost:
                for z in x.card.manacost:
                    if z == 'R':
                        self.red_mana += x.multiplicity
                    elif z== 'U':
                        self.blue_mana += x.multiplicity
                    elif z == 'G':
                        self.green_mana += x.multiplicity
                    elif z == 'B':
                        self.black_mana += x.multiplicity
                    elif z == 'W':
                        self.white_mana += x.multiplicity

            if re.sub('[^0123456789]','',normal):
                self.colorless_mana += int(re.sub('[^0123456789]','',normal))*x.multiplicity
            #find a way to help out Ai algorithm
            
            if x.card.manacost and '/' in x.card.manacost:
                if 'R' in normal:
                    tempRed += x.multiplicity
                if 'U' in normal:
                    tempBlue += x.multiplicity
                if 'G' in normal:
                    tempGreen += x.multiplicity
                if 'B' in normal:
                    tempBlack += x.multiplicity
                if 'W' in normal:
                    tempWhite += x.multiplicity
            else:
                if 'R' in normal:
                    self.red += x.multiplicity
                if 'U' in normal:
                    self.blue += x.multiplicity
                if 'G' in normal:
                    self.green += x.multiplicity
                if 'B' in normal:
                    self.black += x.multiplicity
                if 'W' in normal:
                    self.white += x.multiplicity
                if not ('W' in normal or 'U' in normal or 'B' in normal or 'R' in normal or 'G' in normal):
                    self.colorless += x.multiplicity
            #determines the manacurve of card

            #determines the numbers of types
            
            if x.card.typing.filter(name='Sorcery'):
                self.sorcery_count += x.multiplicity
            if x.card.typing.filter(name='Creature'):
                self.creature_count += x.multiplicity
            if x.card.typing.filter(name='Land'):
                self.land_count += x.multiplicity
            if x.card.typing.filter(name='Instant'):
                self.instant_count += x.multiplicity
            if x.card.typing.filter(name='Artifact'):
                self.artifact_count += x.multiplicity
            if x.card.typing.filter(name='Enchantment'):
                self.enchantment_count += x.multiplicity
            if x.card.typing.filter(name='Planeswalker'):
                self.planeswalker_count += x.multiplicity

            self.number_of_cards += x.multiplicity

        if self.white:
            self.white += tempWhite
        if self.blue:
            self.blue += tempBlue
        if self.black:
            self.black += tempBlack
        if self.red:
            self.red += tempRed
        if self.green:
            self.green += tempGreen
        self.colorless -= self.land_count
        curve[0] -= self.land_count
        #get number of cards
        self.mana_curve=str(curve).strip('[]')
        '''if type(deck) is Deck:
            new = PublishedDeck(name=deck.name,user=deck.user,published=datetime.now(),description='',score=0)
            new.save()
            for count in deck.card_counts.all():
                new_count = CardCount(card=count.card, multiplicity=count.multiplicity)
                new_count.save()
                new.card_counts.add(new_count)
            new.save()
            for count in deck.sb_counts.all():
                new_count = CardCount(card=count.card, multiplicity=count.multiplicity)
                new_count.save()
                new.sb_counts.add(new_count)
            new.save()
            standard = Format.objects.filter(name='standard')[0]
            modern = Format.objects.filter(name='modern')[0]
            legacy = Format.objects.filter(name='legacy')[0]
            vintage = Format.objects.filter(name='vintage')[0]
            commander = Format.objects.filter(name='commander')[0]
            breakdown = Card_Breakdown(deck=new, number_of_cards=0)
            breakdown.initialize(new)
            breakdown.save()
            new.standard_legal = standard.legal(deck)
            new.modern_legal = modern.legal(deck)
            new.legacy_legal = legacy.legal(deck)
            new.vintage_legal = vintage.legal(deck)
            new.commander_legal = commander.legal(deck)
            new.save()
            deck = new'''
        self.deck=str(type(deck))+str(deck.pk)

class Archetype(models.Model):
    colors = models.CharField(max_length=200)
    format = models.CharField(max_length=200)
    lands = models.IntegerField(default=0)
    curve = models.CommaSeparatedIntegerField(max_length=500, default='0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0')
    numDecks = models.IntegerField(default=0)
    cards = models.ManyToManyField('mainsite.Card')

    def __unicode__(self):
        return self.format + ': ' + self.colors

    def update(self, deck):
        breakdown = Card_Breakdown()
        breakdown.initialize(deck)
        breakdown.save()
        #print '\n\n\n\n' + str(breakdown.white) + str(breakdown.blue) + str(breakdown.black) + str(breakdown.red) + str(breakdown.green) + '\n\n\n\n'
        if (breakdown.white > 0 and not 'W' in self.colors.upper()) or (breakdown.blue > 0 and not 'U' in self.colors.upper()) or (breakdown.black > 0 and not 'B' in self.colors.upper()) or (breakdown.red > 0 and not 'R' in self.colors.upper()) or (breakdown.green > 0 and not 'G' in self.colors.upper()):
            return
        self.numDecks += 1
        self.lands += breakdown.land_count
        newCurve = breakdown.mana_curve.split(', ')
        for i in xrange(len(newCurve)):
            if type(newCurve[i]) is unicode:
                newCurve[i] = unicodedata.normalize('NFKD', newCurve[i]).encode('ascii','ignore')
            newCurve[i] = int(newCurve[i])
        curve = self.curve.split(', ')
        for i in xrange(len(curve)):
            if type(curve[i]) is unicode:
                curve[i] = unicodedata.normalize('NFKD', curve[i]).encode('ascii','ignore')
            curve[i] = int(curve[i])
        for i in xrange(len(curve)):
            curve[i] += newCurve[i]
        self.curve = str(curve).strip('[]')
        for card_count in deck.card_counts.all():
            if not self.cards.filter(pk=card_count.card.pk):
                self.cards.add(card_count.card)

    def recommend(self, deck):
        breakdown = Card_Breakdown()
        breakdown.initialize(deck)
        breakdown.save()
        if (breakdown.white == 0 and 'W' in self.colors.upper()) or (breakdown.blue == 0 and 'U' in self.colors.upper()) or (breakdown.black == 0 and 'B' in self.colors.upper()) or (breakdown.red == 0 and 'R' in self.colors.upper()) or (breakdown.green == 0 and 'G' in self.colors.upper()):
            return Recommendation()
        ret = Recommendation()
        print '\n\n\n\n' + str(self.curve) + '\n\n\n\n'
        if self.numDecks > 0:
            if self.lands // self.numDecks > breakdown.land_count:
                lands = self.lands // self.numDecks - breakdown.land_count
                mana = breakdown.white_mana + breakdown.blue_mana + breakdown.black_mana + breakdown.red_mana + breakdown.green_mana
                if mana:
                    ret.plains = int(lands*breakdown.white_mana//mana)
                    ret.islands = int(lands*breakdown.blue_mana//mana)
                    ret.swamps = int(lands*breakdown.black_mana//mana)
                    ret.mountains = int(lands*breakdown.red_mana//mana)
                    ret.forests = int(lands*breakdown.green_mana//mana)
                difference = lands - (ret.plains + ret.islands + ret.swamps + ret.mountains + ret.forests)
                while difference:
                    if breakdown.white and difference:
                        ret.plains += 1
                        difference -= 1
                    if breakdown.blue and difference:
                        ret.islands += 1
                        difference -= 1
                    if breakdown.black and difference:
                        ret.swamps += 1
                        difference -= 1
                    if breakdown.red and difference:
                        ret.mountains += 1
                        difference -= 1
                    if breakdown.green and difference:
                        ret.forests += 1
                        difference -= 1
        curve = breakdown.mana_curve.split(', ')
        for i in xrange(len(curve)):
            if type(curve[i]) is unicode:
                curve[i] = unicodedata.normalize('NFKD', curve[i]).encode('ascii','ignore')
            curve[i] = int(curve[i])
        suggestedCurve = self.curve.split(', ')
        for i in xrange(len(suggestedCurve)):
            if type(suggestedCurve[i]) is unicode:
                suggestedCurve[i] = unicodedata.normalize('NFKD', suggestedCurve[i]).encode('ascii','ignore')
            suggestedCurve[i] = int(suggestedCurve[i])
        for i in xrange(len(curve)):
            #print str(i) + ': ' + str(curve[i]) + ', ' + str(suggestedCurve[i] // self.numDecks)
            #print self.numDecks
            if self.numDecks > 0 and curve[i] < suggestedCurve[i] // self.numDecks:
                for card in self.cards.filter(cmc=i):
                    #if i == 5:
                    #    print card.name
                    ret.cards.add(card)
        '''for card in ret.cards:
            if card.name == 'Black Lotus':
                print card.name
            if card.name == 'Time Walk':
                print card.name'''
        return ret

class Recommendation():
    plains = 0
    islands = 0
    swamps = 0
    mountains = 0
    forests = 0
    cards = set([])

class DynamicIndexSignalProcessor(signals.BaseSignalProcessor):
    def setup(self):
        models.signals.post_save.connect(self.handle_save, sender=PublishedDeck)
        models.signals.post_delete.connect(self.handle_delete, sender=PublishedDeck)
        models.signals.post_save.connect(self.handle_save, sender=User)
        models.signals.post_delete.connect(self.handle_delete, sender=User)

    def teardown(self):
        models.signals.post_save.disconnect(self.handle_save, sender=PublishedDeck)
        models.signals.post_delete.disconnect(self.handle_delete, sender=PublishedDeck)
        models.signals.post_save.disconnect(self.handle_save, sender=User)
        models.signals.post_delete.disconnect(self.handle_delete, sender=User)
