/////////////////////////////////////////////////////////////////////////////
//
// testplayers.inc - тестовые персонажи мира.
//
// Персонаж создаётся обычным клиентским путём (tools/test_create_char.py
// или руками в ClassicUO). Аккаунты заводятся при старте сервера
// (TPEnsureAccounts), а навыки, характеристики, деньги и предметы выдаются
// при первом входе в мир (TPApplyOnLogin) - онлайн-персонажу банк и рюкзак
// создаются надёжно, офлайн-выдача в сейв не попадала.
//
// Выдача идёт один раз: на персонаже ставится CProp с версией набора.
// Если нужно выдать заново (например, после правки конфига) - поднять
// TP_VERSION. Золото досыпается только до нужной суммы, предметы и навыки
// применяются заново.
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
var TP_VERSION      := 2;
var TP_CPROP        := "TestPlayerPrepared";
var TP_MAX_CHARS    := 6;


// "Lumberjacking=100;Carpentry=70" -> массив пар.
// Важно: SplitWords() делит по целой строке-разделителю, а не по набору
// символов, поэтому сначала режем по ";", потом каждую пару по "=".
function TPParseSkills( spec )

	var list := {};
	foreach pair in SplitWords( spec, ";" )
		var words := SplitWords( pair, "=" );
		if( words.Size() < 2 )
			continue;
		endif
		var value := CInt( words[2] );
		if( value < 0 )
			value := 0;
		elseif( value > 100 )
			value := 100;
		endif
		list.Append( struct{ "Name":=words[1], "Value":=value } );
	endforeach
	return list;
endfunction


// Сколько золота уже лежит в контейнере.
function TPCountGold( container )

	var total := 0;
	foreach item in EnumerateItemsInContainer( container )
		if( item.objtype == UOBJ_GOLD_COIN )
			total += item.amount;
		endif
	endforeach
	return total;
endfunction


function TPApplyOne( who, elem )

	var result := struct{ "Skills":=0, "Items":=0, "Gold":=0, "BankGold":=0,
	                      "PackItems":=0, "Message":="" };

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
			// Досыпаем только недостающее: повторный запуск не должен
			// удваивать деньги.
			var missing := gold - TPCountGold( bank );
			if( missing > 0 )
				CreateItemInContainer( bank, UOBJ_GOLD_COIN, missing );
				result.Gold := missing;
			endif
			result.BankGold := TPCountGold( bank );
		endif
	endif

	if( elem.Items )
		foreach entry in SplitWords( elem.Items, "," )
			var count := 1;
			var parts := SplitWords( entry, "*" );
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

	if( who.backpack )
		var pack_items := 0;
		foreach item in EnumerateItemsInContainer( who.backpack )
			pack_items += 1;
		endforeach
		result.PackItems := pack_items;
	endif

	SetObjProperty( who, TP_CPROP, TP_VERSION );
	return result;
endfunction


function TPEnsureAccounts()

	var result := struct{ "Created":=0, "Existing":=0, "Failed":=0, "Message":="" };

	var cfg := ReadConfigFile( TP_CFG );
	if( cfg.errortext )
		result.Message := "не удалось прочитать " + TP_CFG + ": " + cfg.errortext;
		return result;
	endif

	foreach key in GetConfigStringKeys( cfg )
		var elem := FindConfigElem( cfg, key );
		var account := FindAccount( elem.Account );
		if( !account.errortext )
			result.Existing += 1;
			continue;
		endif
		account := CreateAccount( elem.Account, elem.Password, 1 );
		if( account.errortext )
			result.Failed += 1;
			result.Message += "аккаунт " + elem.Account + ": " + account.errortext + "; ";
		else
			result.Created += 1;
			Print( "TestPlayers: создан аккаунт " + elem.Account );
		endif
	endforeach

	return result;
endfunction


// Ищет элемент конфига для вошедшего персонажа (по имени).
function TPFindElem( name )

	var cfg := ReadConfigFile( TP_CFG );
	if( cfg.errortext )
		return 0;
	endif

	foreach key in GetConfigStringKeys( cfg )
		var elem := FindConfigElem( cfg, key );
		var elem_name := elem.Name;
		if( !elem_name )
			elem_name := key;
		endif
		if( elem_name == name )
			return elem;
		endif
	endforeach

	return 0;
endfunction


function TPApplyOnLogin( who )

	if( who.acct.default_cmdlevel > 0 )
		// Админов не трогаем: тестовый набор - для обычных игроков.
		return 0;
	endif

	var elem := TPFindElem( who.name );
	if( TypeOf( elem ) != "ConfigElemRef" )
		return 0;
	endif

	if( CInt( GetObjProperty( who, TP_CPROP ) ) >= TP_VERSION )
		return 0;
	endif

	var prepared := TPApplyOne( who, elem );
	Print( "TestPlayers: " + who.name + " подготовлен: навыков " + prepared.Skills +
	       ", предметов выдано " + prepared.Items + ", золота выдано " + prepared.Gold +
	       "; в банке " + prepared.BankGold + " золота, в рюкзаке " + prepared.PackItems +
	       " предметов" );
	if( prepared.Message )
		Print( "TestPlayers: " + prepared.Message );
	endif
	return 1;
endfunction
