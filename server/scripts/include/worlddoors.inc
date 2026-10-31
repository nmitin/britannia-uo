/////////////////////////////////////////////////////////////////////////////
//
// worlddoors.inc - мировые двери Британии.
//
// В клиентских файлах двери домов не хранятся как статики: на обычных
// шардах они лежат в world save как динамические предметы. После конвертации
// карты из client/ их нет, поэтому расставляем двери из конфигов дистрибутива
// decoratefacets (данные ServUO/RunUO для Felucca).
//
// Расстановка идемпотентна: уже существующая дверь на месте не создаётся
// повторно. Открытые двери при старте закрываются по реестру, чтобы вернуть
// их на исходные координаты (ядро POL сдвигает дверь при открытии на XMod/YMod).
//
/////////////////////////////////////////////////////////////////////////////

use uo;
use os;
use cfgfile;

var WORLDOORS_CFG      := ":decoratefacets:decorations/britannia/doors";
var WORLDOORS_ITEMDESC := ":doors:itemdesc";
var WORLDOORS_REGISTRY := "WorldDoors.Serials";
var WORLDOORS_CPROP    := "WorldDoor";


/////////////////////////////////////////////////////////////////////////////
// Загрузить реестр серийников мировых дверей.
/////////////////////////////////////////////////////////////////////////////
function WorldDoorsLoadRegistry()

	var registry := GetGlobalProperty( WORLDOORS_REGISTRY );

	if( TypeOfInt( registry ) != OT_ARRAY )
		registry := {};
	endif

	return registry;
endfunction


/////////////////////////////////////////////////////////////////////////////
// Сохранить реестр.
/////////////////////////////////////////////////////////////////////////////
function WorldDoorsSaveRegistry( registry )

	SetGlobalProperty( WORLDOORS_REGISTRY, registry );
	return registry;
endfunction


/////////////////////////////////////////////////////////////////////////////
// Закрыть все известные мировые двери, вернув их на исходные координаты.
/////////////////////////////////////////////////////////////////////////////
function WorldDoorsCloseRegistered( registry )

	var closed := 0;

	foreach serial in registry
		var door := SystemFindObjectBySerial( serial );
		if( door && GetObjProperty( door, WORLDOORS_CPROP ) )
			if( door.IsOpen() )
				door.Close();
				closed += 1;
			endif
		endif
	endforeach

	return closed;
endfunction


/////////////////////////////////////////////////////////////////////////////
// Найти уже существующую дверь нужного типа в точке (x,y,z).
//
// Двери с XMod/YMod при открытии сдвигаются ядром на эти величины, поэтому
// проверяем и исходную, и «открытую» позицию. Это страхует от дублей, даже
// если реестр потерян.
/////////////////////////////////////////////////////////////////////////////
function WorldDoorsFindExisting( objtype, x, y, z, realm, xmod, ymod )

	foreach item in ListItemsAtLocation( x, y, z, realm )
		if( item.objtype == objtype )
			return item;
		endif
	endforeach

	if( xmod != 0 || ymod != 0 )
		foreach item in ListItemsAtLocation( x + xmod, y + ymod, z, realm )
			if( item.objtype == objtype )
				return item;
			endif
		endforeach
	endif

	return 0;
endfunction


/////////////////////////////////////////////////////////////////////////////
// Получить XMod/YMod двери из :doors:itemdesc.
/////////////////////////////////////////////////////////////////////////////
function WorldDoorsGetOffset( door_cfg, objtype )

	var elem := FindConfigElem( door_cfg, objtype );
	if( !elem || elem.errortext )
		return struct{ "XMod":=0, "YMod":=0 };
	endif

	return struct{ "XMod":=CInt( elem.XMod ), "YMod":=CInt( elem.YMod ) };
endfunction


/////////////////////////////////////////////////////////////////////////////
// Расставить недостающие мировые двери.
//
// Возвращает struct{ Created, Existing, Failed, Total, Closed, Error }.
/////////////////////////////////////////////////////////////////////////////
function WorldDoorsPlace()

	var result := struct{ "Created":=0, "Existing":=0, "Failed":=0,
	                      "Total":=0, "Closed":=0, "Message":="" };

	var cfg := ReadConfigFile( WORLDOORS_CFG );
	if( cfg.errortext )
		result.Message := "не удалось прочитать " + WORLDOORS_CFG + ": " + cfg.errortext;
		return result;
	endif

	var door_cfg := ReadConfigFile( WORLDOORS_ITEMDESC );
	if( door_cfg.errortext )
		result.Message := "не удалось прочитать " + WORLDOORS_ITEMDESC + ": " + door_cfg.errortext;
		return result;
	endif

	var registry := WorldDoorsLoadRegistry();
	result.Closed := WorldDoorsCloseRegistered( registry );

	// Реестр пересобираем заново: в нём останутся только реально найденные
	// и созданные двери, без устаревших серийников.
	var new_registry := {};
	var keys := GetConfigIntKeys( cfg );
	var i := 0;

	foreach key in keys
		var elem := FindConfigElem( cfg, key );
		var objtype := CInt( elem.Objtype );
		var x := CInt( elem.X );
		var y := CInt( elem.Y );
		var z := CInt( elem.Z );
		var realm := elem.Realm;
		var amount := 1;

		if( !realm )
			realm := "britannia";
		endif
		if( elem.Amount )
			amount := CInt( elem.Amount );
		endif

		var offset := WorldDoorsGetOffset( door_cfg, objtype );
		var existing := WorldDoorsFindExisting( objtype, x, y, z, realm,
		                                        offset.XMod, offset.YMod );

		if( existing )
			// Если дверь была открыта и найдена в сдвинутой позиции — закрываем.
			if( existing.IsOpen() )
				existing.Close();
				result.Closed += 1;
			endif
			// Мировые двери не должны исчезать от таймера распада.
			existing.movable := 0;
			if( existing.decayAt )
				existing.decayAt := 0;
			endif
			new_registry.append( existing.serial );
			result.Existing += 1;
		else
			var door := CreateItemAtLocation( x, y, z, objtype, amount, realm );
			if( door.errortext )
				result.Failed += 1;
				Print( "WorldDoors: не удалось создать дверь " + Hex( objtype ) +
				       " в " + x + "," + y + "," + z + " (" + realm + "): " + door.errortext );
			else
				door.movable := 0;
				door.decayAt := 0;
				SetObjProperty( door, WORLDOORS_CPROP, 1 );
				new_registry.append( door.serial );
				result.Created += 1;
			endif
		endif

		result.Total += 1;
		i += 1;
		if( i % 50 == 0 )
			sleepms( 1 );
		endif
	endforeach

	WorldDoorsSaveRegistry( new_registry );

	return result;
endfunction


/////////////////////////////////////////////////////////////////////////////
// Удалить все мировые двери, известные реестру.
//
// Возвращает struct{ Destroyed, Missing, Error }.
/////////////////////////////////////////////////////////////////////////////
function WorldDoorsRemove()

	var result := struct{ "Destroyed":=0, "Missing":=0, "Message":="" };
	var registry := WorldDoorsLoadRegistry();

	foreach serial in registry
		var door := SystemFindObjectBySerial( serial );
		if( door && GetObjProperty( door, WORLDOORS_CPROP ) )
			DestroyItem( door );
			result.Destroyed += 1;
		else
			result.Missing += 1;
		endif
	endforeach

	WorldDoorsSaveRegistry( {} );
	return result;
endfunction


/////////////////////////////////////////////////////////////////////////////
// Сколько мировых дверей сейчас существует.
/////////////////////////////////////////////////////////////////////////////
function WorldDoorsCount()

	var count := 0;
	foreach serial in WorldDoorsLoadRegistry()
		var door := SystemFindObjectBySerial( serial );
		if( door && GetObjProperty( door, WORLDOORS_CPROP ) )
			count += 1;
		endif
	endforeach

	return count;
endfunction
