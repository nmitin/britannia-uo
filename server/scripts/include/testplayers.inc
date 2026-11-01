/////////////////////////////////////////////////////////////////////////////
//
// testplayers.inc - тестовые персонажи мира.
//
// Персонаж создаётся обычным клиентским путём (tools/test_create_char.py
// или руками в ClassicUO). При старте сервера этот модуль находит его по
// имени, выдаёт навыки, характеристики, деньги в банк и предметы в рюкзак.
//
// Выдача идёт один раз: на персонаже ставится CProp с версией набора.
// Если нужно выдать заново (например, после правки конфига) - поднять
// TP_VERSION.
//
// Конфиг: config/testplayers.cfg.
//
/////////////////////////////////////////////////////////////////////////////

use uo;
use os;
use cfgfile;
include ":containers:storageAreas";
include ":attributes:attributes";
include "include/objtype";

var TP_CFG          := "testplayers";
var TP_VERSION_PROP := "TestPlayers.Version";
var TP_VERSION      := 1;
var TP_CPROP        := "TestPlayerPrepared";
var TP_MAX_CHARS    := 6;


function TPParseSkills( spec )

	var list := {};
	var words := SplitWords( spec, "=;" );
	var pairs := CInt( words.Size() / 2 );
	for i := 1 to pairs
		var value := CInt( words[2*i] );
		if( value < 0 )
			value := 0;
		elseif( value > 100 )
			value := 100;
		endif
		list.Append( struct{ "Name":=words[2*i - 1], "Value":=value } );
	endfor
	return list;
endfunction


function TPApplyOne( who, elem )

	var result := struct{ "Skills":=0, "Items":=0, "Gold":=0, "Message":="" };

	if( elem.Strength )
		SetAttributeBaseValue( who, "Strength", CInt( elem.Strength ) * 10 );
	endif
	if( elem.Dexterity )
		SetAttributeBaseValue( who, "Dexterity", CInt( elem.Dexterity ) * 10 );
	endif
	if( elem.Intelligence )
		SetAttributeBaseValue( who, "Intelligence", CInt( elem.Intelligence ) * 10 );
	endif
	AP_RefreshVitals( who );

	if( elem.Skills )
		foreach skill in TPParseSkills( elem.Skills )
			if( SetAttributeBaseValue( who, skill.Name, skill.Value * 10 ) )
				result.Skills += 1;
			else
				result.Message += "навык " + skill.Name + " не выставлен; ";
			endif
		endforeach
	endif

	var gold := CInt( elem.Gold );
	if( gold > 0 )
		var bank := CP_GetStorageContainerForMobile( who, CP_BANK_AREA, CP_CREATE );
		if( bank.errortext )
			result.Message += "банк: " + bank.errortext + "; ";
		else
			CreateItemInContainer( bank, UOBJ_GOLD_COIN, gold );
			result.Gold := gold;
		endif
	endif

	if( elem.Items )
		foreach entry in SplitWords( elem.Items, "," )
			var count := 1;
			var parts := SplitWords( entry, "x" );
			if( parts.Size() > 1 )
				entry := parts[1];
				count := CInt( parts[2] );
			endif
			var objtype := CInt( entry );
			for i := 1 to count
				var item := CreateItemInContainer( who.backpack, objtype );
				if( item.errortext )
					result.Message += "предмет " + objtype + ": " + item.errortext + "; ";
				else
					result.Items += 1;
				endif
			endfor
		endforeach
	endif

	SetObjProperty( who, TP_CPROP, TP_VERSION );
	return result;
endfunction


function TPApply()

	var result := struct{ "Applied":=0, "Skipped":=0, "Missing":=0,
	                      "Failed":=0, "Total":=0, "Message":="" };

	var cfg := ReadConfigFile( TP_CFG );
	if( cfg.errortext )
		result.Message := "не удалось прочитать " + TP_CFG + ": " + cfg.errortext;
		return result;
	endif

	foreach key in GetConfigStringKeys( cfg )
		var elem := FindConfigElem( cfg, key );
		var name := elem.Name;
		if( !name )
			name := key;
		endif
		result.Total += 1;

		var account := FindAccount( elem.Account );
		if( account.errortext )
			account := CreateAccount( elem.Account, elem.Password, 1 );
			if( account.errortext )
				result.Failed += 1;
				result.Message += "аккаунт " + elem.Account + ": " + account.errortext + "; ";
				continue;
			endif
			Print( "TestPlayers: создан аккаунт " + elem.Account );
		endif

		var who := 0;
		for i := 1 to TP_MAX_CHARS
			var chr := account.GetCharacter( i );
			if( chr && chr.name == name )
				who := chr;
				break;
			endif
			SleepMS( 2 );
		endfor

		if( !who )
			result.Missing += 1;
			Print( "TestPlayers: " + name + " ещё не создан (аккаунт " + elem.Account + ")" );
			continue;
		endif

		if( CInt( GetObjProperty( who, TP_CPROP ) ) >= TP_VERSION )
			result.Skipped += 1;
			continue;
		endif

		var prepared := TPApplyOne( who, elem );
		result.Applied += 1;
		Print( "TestPlayers: " + name + " подготовлен: навыков " + prepared.Skills +
		       ", предметов " + prepared.Items + ", золота " + prepared.Gold );
		if( prepared.Message )
			result.Message += prepared.Message;
		endif
	endforeach

	return result;
endfunction
