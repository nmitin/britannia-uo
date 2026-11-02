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
