

include ":attributes:attributes";
include ":damage:damage";

function main_AI_loop()

    var ev;
    var wanders := 60;
    var next_offer := ReadGameClock();
    var next_wander := 0;
    var evtext;
    var resetquest := 0;

    EnableMainEvents();

    while (1)

	if (ReadGameClock() > next_wander)
        	wander();
		next_wander := ReadGameClock()+2;
		wanders := wanders +1;
		if (wanders > 60)
			wanders :=0;
			if (!look_around())
			if (!resetquest)
				if (master.serial == me.serial)
					if (!slave)
						MoveObjectToLocation(me,5288,1176,0,"britannia_alt",MOVEOBJECT_FORCELOCATION);
						SetObjProperty(me,"guardkill",1);
						KillMobile(me);
					endif
				else
					if (!master)
						MoveObjectToLocation(me,5288, 1176, 0,"britannia_alt",MOVEOBJECT_FORCELOCATION);
						SetObjProperty(me,"guardkill",1);
						KillMobile(me);
					endif
				endif
			else
				MoveObjectToLocation(me,5288, 1176, 0,"britannia_alt",MOVEOBJECT_FORCELOCATION);
				SetObjProperty(me,"guardkill",1);
				me,kill();
			endif
			endif
			ev := sleepmode();
	    	endif
	else
		ev := os::wait_for_event( 3 );
	endif

	if (ev)
        repeat
            case (ev.type)
                SYSEVENT_SPEECH:
	    		next_wander := ReadGameClock()+30;
			evtext := lower(ev.text);
			if (evtext["take"])
				GiveQuestItem(ev.source);
			elseif ( next_offer < ReadGameClock() )
				next_offer := ReadGameClock()+45;
				TurnToward(ev.source);
				if (!OfferQuest())
		    			check_speech(ev.text, ev.source);
				endif
			else
		    		check_speech(ev.text, ev.source);
			endif
		SYSEVENT_ENTEREDAREA:
		    if (!ev.source.isA(POLCLASS_NPC))
		    	YellToFriend(ev.source);
		    endif
                SYSEVENT_ENGAGED:
                SYSEVENT_DAMAGED:
                    Fight( ev.source );
		SYSEVENT_ITEM_GIVEN:
		    wanders :=0;
		    next_wander := ReadGameClock()+30;
		    if ( GetObjProperty(ev.item,"slave") == CInt(me.serial) )
			TakeQuestItem(ev.source,ev.item);
			resetquest := 1;
		    else
			TakeItem(ev.source,ev.item);
		   endif
            endcase
        until (! (ev := os::wait_for_event(2)) );
	endif

   endwhile

endfunction

function look_around()

	foreach critter in ListMobilesNearLocation( me.x,me.y,me.z, 10, me.realm );
          if (!critter.isA(POLCLASS_NPC))
		return 1;
          endif
	endforeach

	return 0;

endfunction

function EnableMainEvents()

    DisableEvents( SYSEVENT_SPEECH + SYSEVENT_LEFTAREA + SYSEVENT_DISENGAGED + SYSEVENT_OPPONENT_MOVED );
    EnableEvents( SYSEVENT_SPEECH, 2 );
    EnableEvents( SYSEVENT_ENGAGED + SYSEVENT_DAMAGED + SYSEVENT_ENTEREDAREA, HALT_THRESHOLD );
    EnableEvents( SYSEVENT_ITEM_GIVEN );

endfunction

function DisableMainEvents()

    DisableEvents( SYSEVENT_SPEECH + SYSEVENT_ENGAGED + SYSEVENT_DAMAGED + SYSEVENT_ENTEREDAREA + SYSEVENT_ITEM_GIVEN );

endfunction

function OfferQuest()

	if ( questtype < 2 )
		return OfferMailBoyQuest();
	endif

	return 0;

endfunction

function OfferMailBoyQuest()

	var item := 0;
	var slavetown;
	if (me.serial == master.serial)
		item := HasQuestItem(me, slave);
		if (item)
			slavetown := GetObjProperty(me,"slavetown");
			say("У меня есть "+ item.desc + ", который нужно доставить "+slave.name+" в " + slavetown);
			sleep(1);
			say("Если ты [возьмёшь] это, "+ slave.name + " заплатит тебе.");
			return 1;
		endif
	else
		if (!master)
			return 0;
		else
			item := HasQuestItem(master, me);
			slavetown := WhatTown(master);
			if ( (item) && (slavetown) )
				say(master.name + " в " + slavetown + " имеет " + item.desc + " для меня.");
				sleep(1);
				say("Если принесёшь это мне, я заплачу.");
				return 1;
			endif
		endif
	endif
	return 0;

endfunction

function GiveQuestItem(you)

	var item := HasQuestItem(me, slave);
	if (item)
		var slavetown := GetObjProperty(me,"slavetown");
		say("Вот "+item.desc+" для "+slave.name+" в "+slavetown);
		say("Отнеси это в "+ slave.name + " за наградой.");
		MoveItemToContainer(item,you.backpack);
	endif

endfunction

function HasQuestItem(who, forwhom)

	foreach item in EnumerateItemsInContainer(who.backpack)
		if ( GetObjProperty(item,"slave") == forwhom.serial )
			return item;
		endif
	endforeach
	return 0;

endfunction

function TakeQuestItem(you, it)

	TurnToward(you);
	say("О, это, должно быть, от "+master.name+"! Спасибо, что принёс!");
	say("А вот твоя плата!");
	DestroyItem(it);
	var goldamount := ((RandomInt(3)+2)*100)+RandomInt(100);
	CreateItemInContainer(you.backpack,"goldcoin",goldamount);

endfunction