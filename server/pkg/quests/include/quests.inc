/////////////////////////////////////////////////////////////////////////////
//
// quests.inc - общие функции квестов (курьерские у торговцев, охота у стражи).
//
/////////////////////////////////////////////////////////////////////////////

use uo;
use os;
use util;
use cfgfile;

var Q_CFG := ":quests:quests";


/////////////////////////////////////////////////////////////////////////////
// Конфиг квестов.
/////////////////////////////////////////////////////////////////////////////
function Q_Config()

	return ReadConfigFile( Q_CFG );
endfunction


/////////////////////////////////////////////////////////////////////////////
// Число из секции Settings.
/////////////////////////////////////////////////////////////////////////////
function Q_Setting( name, default_value )

	var cfg := Q_Config();
	var elem := FindConfigElem( cfg, "Settings" );
	if( !elem || elem.errortext )
		return default_value;
	endif

	var value := GetConfigInt( elem, name );
	if( value == error )
		return default_value;
	endif
	if( !value )
		return default_value;
	endif

	return value;
endfunction


/////////////////////////////////////////////////////////////////////////////
// Русское название города по имени региона ("" - не город).
/////////////////////////////////////////////////////////////////////////////
function Q_TownName( region )

	if( !region )
		return "";
	endif

	var elem := FindConfigElem( Q_Config(), region );
	if( !elem || elem.errortext )
		return "";
	endif

	return GetConfigString( elem, "Name" );
endfunction


/////////////////////////////////////////////////////////////////////////////
// Имя региона-города в точке ("" - точка вне городов из quests.cfg).
/////////////////////////////////////////////////////////////////////////////
function Q_TownAt( x, y, realm )

	var region := GetRegionNameAtLocation( x, y, realm );
	if( !region )
		return "";
	endif
	if( Q_TownName( region ) == "" )
		return "";
	endif

	return region;
endfunction


/////////////////////////////////////////////////////////////////////////////
// Посылка, которую игрок сейчас несёт (или 0).
/////////////////////////////////////////////////////////////////////////////
function Q_FindParcel( player )

	if( !player.backpack )
		return 0;
	endif

	foreach item in EnumerateItemsInContainer( player.backpack )
		if( GetObjProperty( item, "deliverto" ) )
			return item;
		endif
	endforeach

	return 0;
endfunction


/////////////////////////////////////////////////////////////////////////////
// Выбрать торговца-адресата в другом городе (по реестру merchantnodes).
//
// Возвращает struct{ "Npc":=npc, "Town":=region } или 0.
/////////////////////////////////////////////////////////////////////////////
function Q_PickTarget( byref me, mytown )

	var others := {};
	var sames := {};

	var nodes := GetGlobalProperty( "WorldMerchants.Serials" );
	if( TypeOfInt( nodes ) != OT_ARRAY )
		return 0;
	endif

	foreach node_serial in nodes
		var node := SystemFindObjectBySerial( node_serial );
		if( !node )
			continue;
		endif

		var info := GetObjProperty( node, "MerchantInfo" );
		if( !info )
			continue;
		endif

		foreach npc_serial in ( info.Keys() )
			var npc := SystemFindObjectBySerial( CInt( npc_serial ) );
			if( !npc || npc.dead )
				continue;
			endif
			if( npc.serial == me.serial )
				continue;
			endif
			// Только обычные торговцы: у банкиров, лекарей и стейблмастеров
			// свой AI и они не принимают посылки.
			if( npc.script != "merchant" )
				continue;
			endif

			var town := Q_TownAt( npc.x, npc.y, npc.realm );
			if( !town )
				continue;
			endif

			var entry := struct{ "Npc":=npc, "Town":=town };
			if( town == mytown )
				sames.append( entry );
			else
				others.append( entry );
			endif
		endforeach
	endforeach

	if( Len( others ) > 0 )
		return others[RandomInt( Len( others ) ) + 1];
	endif
	if( Len( sames ) > 0 )
		return sames[RandomInt( Len( sames ) ) + 1];
	endif

	return 0;
endfunction

/////////////////////////////////////////////////////////////////////////////
// Направление и расстояние до цели по-русски.
//
// Возвращает фразу вида "совсем рядом, к северо-востоку".
/////////////////////////////////////////////////////////////////////////////
function Q_DirectionPhrase( from_x, from_y, to_x, to_y )

	var ns := "";
	var ew := "";
	var ns_diff := 0;
	var ew_diff := 0;

	if( to_y < from_y )
		ns := "север";
		ns_diff := from_y - to_y;
	elseif( to_y > from_y )
		ns := "юг";
		ns_diff := to_y - from_y;
	endif

	if( to_x < from_x )
		ew := "запад";
		ew_diff := from_x - to_x;
	elseif( to_x > from_x )
		ew := "восток";
		ew_diff := to_x - from_x;
	endif

	// Диагональ только если обе составляющие сопоставимы.
	if( ns != "" && ew != "" )
		if( ns_diff > ew_diff * 2 )
			ew := "";
		elseif( ew_diff > ns_diff * 2 )
			ns := "";
		endif
	endif

	var direction := "";
	if( ns == "север" && ew == "восток" )
		direction := "северо-востоку";
	elseif( ns == "север" && ew == "запад" )
		direction := "северо-западу";
	elseif( ns == "юг" && ew == "восток" )
		direction := "юго-востоку";
	elseif( ns == "юг" && ew == "запад" )
		direction := "юго-западу";
	elseif( ns == "север" )
		direction := "северу";
	elseif( ns == "юг" )
		direction := "югу";
	elseif( ew == "восток" )
		direction := "востоку";
	elseif( ew == "запад" )
		direction := "западу";
	else
		direction := "";
	endif

	var dist := ns_diff;
	if( ew_diff > dist )
		dist := ew_diff;
	endif
	var distance_word := "совсем рядом";
	if( dist > 15 )
		distance_word := "неподалёку";
	endif
	if( dist > 60 )
		distance_word := "далеко";
	endif
	if( dist > 150 )
		distance_word := "очень далеко";
	endif

	if( direction == "" )
		return distance_word;
	endif

	return distance_word + ", к " + direction;
endfunction


/////////////////////////////////////////////////////////////////////////////
// Объяснить игроку, куда нести посылку (для «не того» NPC).
//
// Возвращает 1, если подсказка выдана, и 0, если адресат не найден.
/////////////////////////////////////////////////////////////////////////////
function Q_ExplainDelivery( byref npc, byref player, byref parcel )

	var dest_serial := CInt( GetObjProperty( parcel, "deliverto" ) );
	if( !dest_serial )
		return 0;
	endif

	var dest := SystemFindObjectBySerial( dest_serial );
	if( !dest || dest.dead )
		PrintTextAbovePrivate( npc, "Боюсь, ты уже не найдёшь, кому это отнести.", player );
		return 1;
	endif

	var town := Q_TownAt( dest.x, dest.y, dest.realm );
	var town_name := Q_TownName( town );
	var phrase := Q_DirectionPhrase( npc.x, npc.y, dest.x, dest.y );

	if( town_name != "" )
		PrintTextAbovePrivate( npc, "Это не мне. " + dest.name + " сейчас в городе " +
		                       town_name + ", это " + phrase + ".", player );
	else
		PrintTextAbovePrivate( npc, "Это не мне. Ищи " + dest.name + ", это " + phrase + ".", player );
	endif

	return 1;
endfunction
