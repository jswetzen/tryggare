
/**
 * Client
**/

import * as runtime from './runtime/library.js';
import $Types = runtime.Types // general types
import $Public = runtime.Types.Public
import $Utils = runtime.Types.Utils
import $Extensions = runtime.Types.Extensions
import $Result = runtime.Types.Result

export type PrismaPromise<T> = $Public.PrismaPromise<T>


/**
 * Model AdminUser
 * 
 */
export type AdminUser = $Result.DefaultSelection<Prisma.$AdminUserPayload>
/**
 * Model Family
 * 
 */
export type Family = $Result.DefaultSelection<Prisma.$FamilyPayload>
/**
 * Model Parent
 * 
 */
export type Parent = $Result.DefaultSelection<Prisma.$ParentPayload>
/**
 * Model Child
 * 
 */
export type Child = $Result.DefaultSelection<Prisma.$ChildPayload>
/**
 * Model Event
 * 
 */
export type Event = $Result.DefaultSelection<Prisma.$EventPayload>
/**
 * Model Session
 * 
 */
export type Session = $Result.DefaultSelection<Prisma.$SessionPayload>
/**
 * Model Ticket
 * 
 */
export type Ticket = $Result.DefaultSelection<Prisma.$TicketPayload>
/**
 * Model CheckInRecord
 * 
 */
export type CheckInRecord = $Result.DefaultSelection<Prisma.$CheckInRecordPayload>
/**
 * Model AuditLog
 * 
 */
export type AuditLog = $Result.DefaultSelection<Prisma.$AuditLogPayload>

/**
 * ##  Prisma Client ʲˢ
 *
 * Type-safe database client for TypeScript & Node.js
 * @example
 * ```
 * const prisma = new PrismaClient()
 * // Fetch zero or more AdminUsers
 * const adminUsers = await prisma.adminUser.findMany()
 * ```
 *
 *
 * Read more in our [docs](https://www.prisma.io/docs/reference/tools-and-interfaces/prisma-client).
 */
export class PrismaClient<
  ClientOptions extends Prisma.PrismaClientOptions = Prisma.PrismaClientOptions,
  const U = 'log' extends keyof ClientOptions ? ClientOptions['log'] extends Array<Prisma.LogLevel | Prisma.LogDefinition> ? Prisma.GetEvents<ClientOptions['log']> : never : never,
  ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs
> {
  [K: symbol]: { types: Prisma.TypeMap<ExtArgs>['other'] }

    /**
   * ##  Prisma Client ʲˢ
   *
   * Type-safe database client for TypeScript & Node.js
   * @example
   * ```
   * const prisma = new PrismaClient()
   * // Fetch zero or more AdminUsers
   * const adminUsers = await prisma.adminUser.findMany()
   * ```
   *
   *
   * Read more in our [docs](https://www.prisma.io/docs/reference/tools-and-interfaces/prisma-client).
   */

  constructor(optionsArg ?: Prisma.Subset<ClientOptions, Prisma.PrismaClientOptions>);
  $on<V extends U>(eventType: V, callback: (event: V extends 'query' ? Prisma.QueryEvent : Prisma.LogEvent) => void): PrismaClient;

  /**
   * Connect with the database
   */
  $connect(): $Utils.JsPromise<void>;

  /**
   * Disconnect from the database
   */
  $disconnect(): $Utils.JsPromise<void>;

/**
   * Executes a prepared raw query and returns the number of affected rows.
   * @example
   * ```
   * const result = await prisma.$executeRaw`UPDATE User SET cool = ${true} WHERE email = ${'user@email.com'};`
   * ```
   *
   * Read more in our [docs](https://www.prisma.io/docs/reference/tools-and-interfaces/prisma-client/raw-database-access).
   */
  $executeRaw<T = unknown>(query: TemplateStringsArray | Prisma.Sql, ...values: any[]): Prisma.PrismaPromise<number>;

  /**
   * Executes a raw query and returns the number of affected rows.
   * Susceptible to SQL injections, see documentation.
   * @example
   * ```
   * const result = await prisma.$executeRawUnsafe('UPDATE User SET cool = $1 WHERE email = $2 ;', true, 'user@email.com')
   * ```
   *
   * Read more in our [docs](https://www.prisma.io/docs/reference/tools-and-interfaces/prisma-client/raw-database-access).
   */
  $executeRawUnsafe<T = unknown>(query: string, ...values: any[]): Prisma.PrismaPromise<number>;

  /**
   * Performs a prepared raw query and returns the `SELECT` data.
   * @example
   * ```
   * const result = await prisma.$queryRaw`SELECT * FROM User WHERE id = ${1} OR email = ${'user@email.com'};`
   * ```
   *
   * Read more in our [docs](https://www.prisma.io/docs/reference/tools-and-interfaces/prisma-client/raw-database-access).
   */
  $queryRaw<T = unknown>(query: TemplateStringsArray | Prisma.Sql, ...values: any[]): Prisma.PrismaPromise<T>;

  /**
   * Performs a raw query and returns the `SELECT` data.
   * Susceptible to SQL injections, see documentation.
   * @example
   * ```
   * const result = await prisma.$queryRawUnsafe('SELECT * FROM User WHERE id = $1 OR email = $2;', 1, 'user@email.com')
   * ```
   *
   * Read more in our [docs](https://www.prisma.io/docs/reference/tools-and-interfaces/prisma-client/raw-database-access).
   */
  $queryRawUnsafe<T = unknown>(query: string, ...values: any[]): Prisma.PrismaPromise<T>;


  /**
   * Allows the running of a sequence of read/write operations that are guaranteed to either succeed or fail as a whole.
   * @example
   * ```
   * const [george, bob, alice] = await prisma.$transaction([
   *   prisma.user.create({ data: { name: 'George' } }),
   *   prisma.user.create({ data: { name: 'Bob' } }),
   *   prisma.user.create({ data: { name: 'Alice' } }),
   * ])
   * ```
   * 
   * Read more in our [docs](https://www.prisma.io/docs/concepts/components/prisma-client/transactions).
   */
  $transaction<P extends Prisma.PrismaPromise<any>[]>(arg: [...P], options?: { isolationLevel?: Prisma.TransactionIsolationLevel }): $Utils.JsPromise<runtime.Types.Utils.UnwrapTuple<P>>

  $transaction<R>(fn: (prisma: Omit<PrismaClient, runtime.ITXClientDenyList>) => $Utils.JsPromise<R>, options?: { maxWait?: number, timeout?: number, isolationLevel?: Prisma.TransactionIsolationLevel }): $Utils.JsPromise<R>


  $extends: $Extensions.ExtendsHook<"extends", Prisma.TypeMapCb<ClientOptions>, ExtArgs, $Utils.Call<Prisma.TypeMapCb<ClientOptions>, {
    extArgs: ExtArgs
  }>>

      /**
   * `prisma.adminUser`: Exposes CRUD operations for the **AdminUser** model.
    * Example usage:
    * ```ts
    * // Fetch zero or more AdminUsers
    * const adminUsers = await prisma.adminUser.findMany()
    * ```
    */
  get adminUser(): Prisma.AdminUserDelegate<ExtArgs, ClientOptions>;

  /**
   * `prisma.family`: Exposes CRUD operations for the **Family** model.
    * Example usage:
    * ```ts
    * // Fetch zero or more Families
    * const families = await prisma.family.findMany()
    * ```
    */
  get family(): Prisma.FamilyDelegate<ExtArgs, ClientOptions>;

  /**
   * `prisma.parent`: Exposes CRUD operations for the **Parent** model.
    * Example usage:
    * ```ts
    * // Fetch zero or more Parents
    * const parents = await prisma.parent.findMany()
    * ```
    */
  get parent(): Prisma.ParentDelegate<ExtArgs, ClientOptions>;

  /**
   * `prisma.child`: Exposes CRUD operations for the **Child** model.
    * Example usage:
    * ```ts
    * // Fetch zero or more Children
    * const children = await prisma.child.findMany()
    * ```
    */
  get child(): Prisma.ChildDelegate<ExtArgs, ClientOptions>;

  /**
   * `prisma.event`: Exposes CRUD operations for the **Event** model.
    * Example usage:
    * ```ts
    * // Fetch zero or more Events
    * const events = await prisma.event.findMany()
    * ```
    */
  get event(): Prisma.EventDelegate<ExtArgs, ClientOptions>;

  /**
   * `prisma.session`: Exposes CRUD operations for the **Session** model.
    * Example usage:
    * ```ts
    * // Fetch zero or more Sessions
    * const sessions = await prisma.session.findMany()
    * ```
    */
  get session(): Prisma.SessionDelegate<ExtArgs, ClientOptions>;

  /**
   * `prisma.ticket`: Exposes CRUD operations for the **Ticket** model.
    * Example usage:
    * ```ts
    * // Fetch zero or more Tickets
    * const tickets = await prisma.ticket.findMany()
    * ```
    */
  get ticket(): Prisma.TicketDelegate<ExtArgs, ClientOptions>;

  /**
   * `prisma.checkInRecord`: Exposes CRUD operations for the **CheckInRecord** model.
    * Example usage:
    * ```ts
    * // Fetch zero or more CheckInRecords
    * const checkInRecords = await prisma.checkInRecord.findMany()
    * ```
    */
  get checkInRecord(): Prisma.CheckInRecordDelegate<ExtArgs, ClientOptions>;

  /**
   * `prisma.auditLog`: Exposes CRUD operations for the **AuditLog** model.
    * Example usage:
    * ```ts
    * // Fetch zero or more AuditLogs
    * const auditLogs = await prisma.auditLog.findMany()
    * ```
    */
  get auditLog(): Prisma.AuditLogDelegate<ExtArgs, ClientOptions>;
}

export namespace Prisma {
  export import DMMF = runtime.DMMF

  export type PrismaPromise<T> = $Public.PrismaPromise<T>

  /**
   * Validator
   */
  export import validator = runtime.Public.validator

  /**
   * Prisma Errors
   */
  export import PrismaClientKnownRequestError = runtime.PrismaClientKnownRequestError
  export import PrismaClientUnknownRequestError = runtime.PrismaClientUnknownRequestError
  export import PrismaClientRustPanicError = runtime.PrismaClientRustPanicError
  export import PrismaClientInitializationError = runtime.PrismaClientInitializationError
  export import PrismaClientValidationError = runtime.PrismaClientValidationError

  /**
   * Re-export of sql-template-tag
   */
  export import sql = runtime.sqltag
  export import empty = runtime.empty
  export import join = runtime.join
  export import raw = runtime.raw
  export import Sql = runtime.Sql



  /**
   * Decimal.js
   */
  export import Decimal = runtime.Decimal

  export type DecimalJsLike = runtime.DecimalJsLike

  /**
   * Metrics
   */
  export type Metrics = runtime.Metrics
  export type Metric<T> = runtime.Metric<T>
  export type MetricHistogram = runtime.MetricHistogram
  export type MetricHistogramBucket = runtime.MetricHistogramBucket

  /**
  * Extensions
  */
  export import Extension = $Extensions.UserArgs
  export import getExtensionContext = runtime.Extensions.getExtensionContext
  export import Args = $Public.Args
  export import Payload = $Public.Payload
  export import Result = $Public.Result
  export import Exact = $Public.Exact

  /**
   * Prisma Client JS version: 6.19.0
   * Query Engine version: 2ba551f319ab1df4bc874a89965d8b3641056773
   */
  export type PrismaVersion = {
    client: string
  }

  export const prismaVersion: PrismaVersion

  /**
   * Utility Types
   */


  export import Bytes = runtime.Bytes
  export import JsonObject = runtime.JsonObject
  export import JsonArray = runtime.JsonArray
  export import JsonValue = runtime.JsonValue
  export import InputJsonObject = runtime.InputJsonObject
  export import InputJsonArray = runtime.InputJsonArray
  export import InputJsonValue = runtime.InputJsonValue

  /**
   * Types of the values used to represent different kinds of `null` values when working with JSON fields.
   *
   * @see https://www.prisma.io/docs/concepts/components/prisma-client/working-with-fields/working-with-json-fields#filtering-on-a-json-field
   */
  namespace NullTypes {
    /**
    * Type of `Prisma.DbNull`.
    *
    * You cannot use other instances of this class. Please use the `Prisma.DbNull` value.
    *
    * @see https://www.prisma.io/docs/concepts/components/prisma-client/working-with-fields/working-with-json-fields#filtering-on-a-json-field
    */
    class DbNull {
      private DbNull: never
      private constructor()
    }

    /**
    * Type of `Prisma.JsonNull`.
    *
    * You cannot use other instances of this class. Please use the `Prisma.JsonNull` value.
    *
    * @see https://www.prisma.io/docs/concepts/components/prisma-client/working-with-fields/working-with-json-fields#filtering-on-a-json-field
    */
    class JsonNull {
      private JsonNull: never
      private constructor()
    }

    /**
    * Type of `Prisma.AnyNull`.
    *
    * You cannot use other instances of this class. Please use the `Prisma.AnyNull` value.
    *
    * @see https://www.prisma.io/docs/concepts/components/prisma-client/working-with-fields/working-with-json-fields#filtering-on-a-json-field
    */
    class AnyNull {
      private AnyNull: never
      private constructor()
    }
  }

  /**
   * Helper for filtering JSON entries that have `null` on the database (empty on the db)
   *
   * @see https://www.prisma.io/docs/concepts/components/prisma-client/working-with-fields/working-with-json-fields#filtering-on-a-json-field
   */
  export const DbNull: NullTypes.DbNull

  /**
   * Helper for filtering JSON entries that have JSON `null` values (not empty on the db)
   *
   * @see https://www.prisma.io/docs/concepts/components/prisma-client/working-with-fields/working-with-json-fields#filtering-on-a-json-field
   */
  export const JsonNull: NullTypes.JsonNull

  /**
   * Helper for filtering JSON entries that are `Prisma.DbNull` or `Prisma.JsonNull`
   *
   * @see https://www.prisma.io/docs/concepts/components/prisma-client/working-with-fields/working-with-json-fields#filtering-on-a-json-field
   */
  export const AnyNull: NullTypes.AnyNull

  type SelectAndInclude = {
    select: any
    include: any
  }

  type SelectAndOmit = {
    select: any
    omit: any
  }

  /**
   * Get the type of the value, that the Promise holds.
   */
  export type PromiseType<T extends PromiseLike<any>> = T extends PromiseLike<infer U> ? U : T;

  /**
   * Get the return type of a function which returns a Promise.
   */
  export type PromiseReturnType<T extends (...args: any) => $Utils.JsPromise<any>> = PromiseType<ReturnType<T>>

  /**
   * From T, pick a set of properties whose keys are in the union K
   */
  type Prisma__Pick<T, K extends keyof T> = {
      [P in K]: T[P];
  };


  export type Enumerable<T> = T | Array<T>;

  export type RequiredKeys<T> = {
    [K in keyof T]-?: {} extends Prisma__Pick<T, K> ? never : K
  }[keyof T]

  export type TruthyKeys<T> = keyof {
    [K in keyof T as T[K] extends false | undefined | null ? never : K]: K
  }

  export type TrueKeys<T> = TruthyKeys<Prisma__Pick<T, RequiredKeys<T>>>

  /**
   * Subset
   * @desc From `T` pick properties that exist in `U`. Simple version of Intersection
   */
  export type Subset<T, U> = {
    [key in keyof T]: key extends keyof U ? T[key] : never;
  };

  /**
   * SelectSubset
   * @desc From `T` pick properties that exist in `U`. Simple version of Intersection.
   * Additionally, it validates, if both select and include are present. If the case, it errors.
   */
  export type SelectSubset<T, U> = {
    [key in keyof T]: key extends keyof U ? T[key] : never
  } &
    (T extends SelectAndInclude
      ? 'Please either choose `select` or `include`.'
      : T extends SelectAndOmit
        ? 'Please either choose `select` or `omit`.'
        : {})

  /**
   * Subset + Intersection
   * @desc From `T` pick properties that exist in `U` and intersect `K`
   */
  export type SubsetIntersection<T, U, K> = {
    [key in keyof T]: key extends keyof U ? T[key] : never
  } &
    K

  type Without<T, U> = { [P in Exclude<keyof T, keyof U>]?: never };

  /**
   * XOR is needed to have a real mutually exclusive union type
   * https://stackoverflow.com/questions/42123407/does-typescript-support-mutually-exclusive-types
   */
  type XOR<T, U> =
    T extends object ?
    U extends object ?
      (Without<T, U> & U) | (Without<U, T> & T)
    : U : T


  /**
   * Is T a Record?
   */
  type IsObject<T extends any> = T extends Array<any>
  ? False
  : T extends Date
  ? False
  : T extends Uint8Array
  ? False
  : T extends BigInt
  ? False
  : T extends object
  ? True
  : False


  /**
   * If it's T[], return T
   */
  export type UnEnumerate<T extends unknown> = T extends Array<infer U> ? U : T

  /**
   * From ts-toolbelt
   */

  type __Either<O extends object, K extends Key> = Omit<O, K> &
    {
      // Merge all but K
      [P in K]: Prisma__Pick<O, P & keyof O> // With K possibilities
    }[K]

  type EitherStrict<O extends object, K extends Key> = Strict<__Either<O, K>>

  type EitherLoose<O extends object, K extends Key> = ComputeRaw<__Either<O, K>>

  type _Either<
    O extends object,
    K extends Key,
    strict extends Boolean
  > = {
    1: EitherStrict<O, K>
    0: EitherLoose<O, K>
  }[strict]

  type Either<
    O extends object,
    K extends Key,
    strict extends Boolean = 1
  > = O extends unknown ? _Either<O, K, strict> : never

  export type Union = any

  type PatchUndefined<O extends object, O1 extends object> = {
    [K in keyof O]: O[K] extends undefined ? At<O1, K> : O[K]
  } & {}

  /** Helper Types for "Merge" **/
  export type IntersectOf<U extends Union> = (
    U extends unknown ? (k: U) => void : never
  ) extends (k: infer I) => void
    ? I
    : never

  export type Overwrite<O extends object, O1 extends object> = {
      [K in keyof O]: K extends keyof O1 ? O1[K] : O[K];
  } & {};

  type _Merge<U extends object> = IntersectOf<Overwrite<U, {
      [K in keyof U]-?: At<U, K>;
  }>>;

  type Key = string | number | symbol;
  type AtBasic<O extends object, K extends Key> = K extends keyof O ? O[K] : never;
  type AtStrict<O extends object, K extends Key> = O[K & keyof O];
  type AtLoose<O extends object, K extends Key> = O extends unknown ? AtStrict<O, K> : never;
  export type At<O extends object, K extends Key, strict extends Boolean = 1> = {
      1: AtStrict<O, K>;
      0: AtLoose<O, K>;
  }[strict];

  export type ComputeRaw<A extends any> = A extends Function ? A : {
    [K in keyof A]: A[K];
  } & {};

  export type OptionalFlat<O> = {
    [K in keyof O]?: O[K];
  } & {};

  type _Record<K extends keyof any, T> = {
    [P in K]: T;
  };

  // cause typescript not to expand types and preserve names
  type NoExpand<T> = T extends unknown ? T : never;

  // this type assumes the passed object is entirely optional
  type AtLeast<O extends object, K extends string> = NoExpand<
    O extends unknown
    ? | (K extends keyof O ? { [P in K]: O[P] } & O : O)
      | {[P in keyof O as P extends K ? P : never]-?: O[P]} & O
    : never>;

  type _Strict<U, _U = U> = U extends unknown ? U & OptionalFlat<_Record<Exclude<Keys<_U>, keyof U>, never>> : never;

  export type Strict<U extends object> = ComputeRaw<_Strict<U>>;
  /** End Helper Types for "Merge" **/

  export type Merge<U extends object> = ComputeRaw<_Merge<Strict<U>>>;

  /**
  A [[Boolean]]
  */
  export type Boolean = True | False

  // /**
  // 1
  // */
  export type True = 1

  /**
  0
  */
  export type False = 0

  export type Not<B extends Boolean> = {
    0: 1
    1: 0
  }[B]

  export type Extends<A1 extends any, A2 extends any> = [A1] extends [never]
    ? 0 // anything `never` is false
    : A1 extends A2
    ? 1
    : 0

  export type Has<U extends Union, U1 extends Union> = Not<
    Extends<Exclude<U1, U>, U1>
  >

  export type Or<B1 extends Boolean, B2 extends Boolean> = {
    0: {
      0: 0
      1: 1
    }
    1: {
      0: 1
      1: 1
    }
  }[B1][B2]

  export type Keys<U extends Union> = U extends unknown ? keyof U : never

  type Cast<A, B> = A extends B ? A : B;

  export const type: unique symbol;



  /**
   * Used by group by
   */

  export type GetScalarType<T, O> = O extends object ? {
    [P in keyof T]: P extends keyof O
      ? O[P]
      : never
  } : never

  type FieldPaths<
    T,
    U = Omit<T, '_avg' | '_sum' | '_count' | '_min' | '_max'>
  > = IsObject<T> extends True ? U : T

  type GetHavingFields<T> = {
    [K in keyof T]: Or<
      Or<Extends<'OR', K>, Extends<'AND', K>>,
      Extends<'NOT', K>
    > extends True
      ? // infer is only needed to not hit TS limit
        // based on the brilliant idea of Pierre-Antoine Mills
        // https://github.com/microsoft/TypeScript/issues/30188#issuecomment-478938437
        T[K] extends infer TK
        ? GetHavingFields<UnEnumerate<TK> extends object ? Merge<UnEnumerate<TK>> : never>
        : never
      : {} extends FieldPaths<T[K]>
      ? never
      : K
  }[keyof T]

  /**
   * Convert tuple to union
   */
  type _TupleToUnion<T> = T extends (infer E)[] ? E : never
  type TupleToUnion<K extends readonly any[]> = _TupleToUnion<K>
  type MaybeTupleToUnion<T> = T extends any[] ? TupleToUnion<T> : T

  /**
   * Like `Pick`, but additionally can also accept an array of keys
   */
  type PickEnumerable<T, K extends Enumerable<keyof T> | keyof T> = Prisma__Pick<T, MaybeTupleToUnion<K>>

  /**
   * Exclude all keys with underscores
   */
  type ExcludeUnderscoreKeys<T extends string> = T extends `_${string}` ? never : T


  export type FieldRef<Model, FieldType> = runtime.FieldRef<Model, FieldType>

  type FieldRefInputType<Model, FieldType> = Model extends never ? never : FieldRef<Model, FieldType>


  export const ModelName: {
    AdminUser: 'AdminUser',
    Family: 'Family',
    Parent: 'Parent',
    Child: 'Child',
    Event: 'Event',
    Session: 'Session',
    Ticket: 'Ticket',
    CheckInRecord: 'CheckInRecord',
    AuditLog: 'AuditLog'
  };

  export type ModelName = (typeof ModelName)[keyof typeof ModelName]


  export type Datasources = {
    db?: Datasource
  }

  interface TypeMapCb<ClientOptions = {}> extends $Utils.Fn<{extArgs: $Extensions.InternalArgs }, $Utils.Record<string, any>> {
    returns: Prisma.TypeMap<this['params']['extArgs'], ClientOptions extends { omit: infer OmitOptions } ? OmitOptions : {}>
  }

  export type TypeMap<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs, GlobalOmitOptions = {}> = {
    globalOmitOptions: {
      omit: GlobalOmitOptions
    }
    meta: {
      modelProps: "adminUser" | "family" | "parent" | "child" | "event" | "session" | "ticket" | "checkInRecord" | "auditLog"
      txIsolationLevel: Prisma.TransactionIsolationLevel
    }
    model: {
      AdminUser: {
        payload: Prisma.$AdminUserPayload<ExtArgs>
        fields: Prisma.AdminUserFieldRefs
        operations: {
          findUnique: {
            args: Prisma.AdminUserFindUniqueArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$AdminUserPayload> | null
          }
          findUniqueOrThrow: {
            args: Prisma.AdminUserFindUniqueOrThrowArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$AdminUserPayload>
          }
          findFirst: {
            args: Prisma.AdminUserFindFirstArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$AdminUserPayload> | null
          }
          findFirstOrThrow: {
            args: Prisma.AdminUserFindFirstOrThrowArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$AdminUserPayload>
          }
          findMany: {
            args: Prisma.AdminUserFindManyArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$AdminUserPayload>[]
          }
          create: {
            args: Prisma.AdminUserCreateArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$AdminUserPayload>
          }
          createMany: {
            args: Prisma.AdminUserCreateManyArgs<ExtArgs>
            result: BatchPayload
          }
          createManyAndReturn: {
            args: Prisma.AdminUserCreateManyAndReturnArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$AdminUserPayload>[]
          }
          delete: {
            args: Prisma.AdminUserDeleteArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$AdminUserPayload>
          }
          update: {
            args: Prisma.AdminUserUpdateArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$AdminUserPayload>
          }
          deleteMany: {
            args: Prisma.AdminUserDeleteManyArgs<ExtArgs>
            result: BatchPayload
          }
          updateMany: {
            args: Prisma.AdminUserUpdateManyArgs<ExtArgs>
            result: BatchPayload
          }
          updateManyAndReturn: {
            args: Prisma.AdminUserUpdateManyAndReturnArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$AdminUserPayload>[]
          }
          upsert: {
            args: Prisma.AdminUserUpsertArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$AdminUserPayload>
          }
          aggregate: {
            args: Prisma.AdminUserAggregateArgs<ExtArgs>
            result: $Utils.Optional<AggregateAdminUser>
          }
          groupBy: {
            args: Prisma.AdminUserGroupByArgs<ExtArgs>
            result: $Utils.Optional<AdminUserGroupByOutputType>[]
          }
          count: {
            args: Prisma.AdminUserCountArgs<ExtArgs>
            result: $Utils.Optional<AdminUserCountAggregateOutputType> | number
          }
        }
      }
      Family: {
        payload: Prisma.$FamilyPayload<ExtArgs>
        fields: Prisma.FamilyFieldRefs
        operations: {
          findUnique: {
            args: Prisma.FamilyFindUniqueArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$FamilyPayload> | null
          }
          findUniqueOrThrow: {
            args: Prisma.FamilyFindUniqueOrThrowArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$FamilyPayload>
          }
          findFirst: {
            args: Prisma.FamilyFindFirstArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$FamilyPayload> | null
          }
          findFirstOrThrow: {
            args: Prisma.FamilyFindFirstOrThrowArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$FamilyPayload>
          }
          findMany: {
            args: Prisma.FamilyFindManyArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$FamilyPayload>[]
          }
          create: {
            args: Prisma.FamilyCreateArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$FamilyPayload>
          }
          createMany: {
            args: Prisma.FamilyCreateManyArgs<ExtArgs>
            result: BatchPayload
          }
          createManyAndReturn: {
            args: Prisma.FamilyCreateManyAndReturnArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$FamilyPayload>[]
          }
          delete: {
            args: Prisma.FamilyDeleteArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$FamilyPayload>
          }
          update: {
            args: Prisma.FamilyUpdateArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$FamilyPayload>
          }
          deleteMany: {
            args: Prisma.FamilyDeleteManyArgs<ExtArgs>
            result: BatchPayload
          }
          updateMany: {
            args: Prisma.FamilyUpdateManyArgs<ExtArgs>
            result: BatchPayload
          }
          updateManyAndReturn: {
            args: Prisma.FamilyUpdateManyAndReturnArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$FamilyPayload>[]
          }
          upsert: {
            args: Prisma.FamilyUpsertArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$FamilyPayload>
          }
          aggregate: {
            args: Prisma.FamilyAggregateArgs<ExtArgs>
            result: $Utils.Optional<AggregateFamily>
          }
          groupBy: {
            args: Prisma.FamilyGroupByArgs<ExtArgs>
            result: $Utils.Optional<FamilyGroupByOutputType>[]
          }
          count: {
            args: Prisma.FamilyCountArgs<ExtArgs>
            result: $Utils.Optional<FamilyCountAggregateOutputType> | number
          }
        }
      }
      Parent: {
        payload: Prisma.$ParentPayload<ExtArgs>
        fields: Prisma.ParentFieldRefs
        operations: {
          findUnique: {
            args: Prisma.ParentFindUniqueArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$ParentPayload> | null
          }
          findUniqueOrThrow: {
            args: Prisma.ParentFindUniqueOrThrowArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$ParentPayload>
          }
          findFirst: {
            args: Prisma.ParentFindFirstArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$ParentPayload> | null
          }
          findFirstOrThrow: {
            args: Prisma.ParentFindFirstOrThrowArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$ParentPayload>
          }
          findMany: {
            args: Prisma.ParentFindManyArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$ParentPayload>[]
          }
          create: {
            args: Prisma.ParentCreateArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$ParentPayload>
          }
          createMany: {
            args: Prisma.ParentCreateManyArgs<ExtArgs>
            result: BatchPayload
          }
          createManyAndReturn: {
            args: Prisma.ParentCreateManyAndReturnArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$ParentPayload>[]
          }
          delete: {
            args: Prisma.ParentDeleteArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$ParentPayload>
          }
          update: {
            args: Prisma.ParentUpdateArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$ParentPayload>
          }
          deleteMany: {
            args: Prisma.ParentDeleteManyArgs<ExtArgs>
            result: BatchPayload
          }
          updateMany: {
            args: Prisma.ParentUpdateManyArgs<ExtArgs>
            result: BatchPayload
          }
          updateManyAndReturn: {
            args: Prisma.ParentUpdateManyAndReturnArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$ParentPayload>[]
          }
          upsert: {
            args: Prisma.ParentUpsertArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$ParentPayload>
          }
          aggregate: {
            args: Prisma.ParentAggregateArgs<ExtArgs>
            result: $Utils.Optional<AggregateParent>
          }
          groupBy: {
            args: Prisma.ParentGroupByArgs<ExtArgs>
            result: $Utils.Optional<ParentGroupByOutputType>[]
          }
          count: {
            args: Prisma.ParentCountArgs<ExtArgs>
            result: $Utils.Optional<ParentCountAggregateOutputType> | number
          }
        }
      }
      Child: {
        payload: Prisma.$ChildPayload<ExtArgs>
        fields: Prisma.ChildFieldRefs
        operations: {
          findUnique: {
            args: Prisma.ChildFindUniqueArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$ChildPayload> | null
          }
          findUniqueOrThrow: {
            args: Prisma.ChildFindUniqueOrThrowArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$ChildPayload>
          }
          findFirst: {
            args: Prisma.ChildFindFirstArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$ChildPayload> | null
          }
          findFirstOrThrow: {
            args: Prisma.ChildFindFirstOrThrowArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$ChildPayload>
          }
          findMany: {
            args: Prisma.ChildFindManyArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$ChildPayload>[]
          }
          create: {
            args: Prisma.ChildCreateArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$ChildPayload>
          }
          createMany: {
            args: Prisma.ChildCreateManyArgs<ExtArgs>
            result: BatchPayload
          }
          createManyAndReturn: {
            args: Prisma.ChildCreateManyAndReturnArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$ChildPayload>[]
          }
          delete: {
            args: Prisma.ChildDeleteArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$ChildPayload>
          }
          update: {
            args: Prisma.ChildUpdateArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$ChildPayload>
          }
          deleteMany: {
            args: Prisma.ChildDeleteManyArgs<ExtArgs>
            result: BatchPayload
          }
          updateMany: {
            args: Prisma.ChildUpdateManyArgs<ExtArgs>
            result: BatchPayload
          }
          updateManyAndReturn: {
            args: Prisma.ChildUpdateManyAndReturnArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$ChildPayload>[]
          }
          upsert: {
            args: Prisma.ChildUpsertArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$ChildPayload>
          }
          aggregate: {
            args: Prisma.ChildAggregateArgs<ExtArgs>
            result: $Utils.Optional<AggregateChild>
          }
          groupBy: {
            args: Prisma.ChildGroupByArgs<ExtArgs>
            result: $Utils.Optional<ChildGroupByOutputType>[]
          }
          count: {
            args: Prisma.ChildCountArgs<ExtArgs>
            result: $Utils.Optional<ChildCountAggregateOutputType> | number
          }
        }
      }
      Event: {
        payload: Prisma.$EventPayload<ExtArgs>
        fields: Prisma.EventFieldRefs
        operations: {
          findUnique: {
            args: Prisma.EventFindUniqueArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$EventPayload> | null
          }
          findUniqueOrThrow: {
            args: Prisma.EventFindUniqueOrThrowArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$EventPayload>
          }
          findFirst: {
            args: Prisma.EventFindFirstArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$EventPayload> | null
          }
          findFirstOrThrow: {
            args: Prisma.EventFindFirstOrThrowArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$EventPayload>
          }
          findMany: {
            args: Prisma.EventFindManyArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$EventPayload>[]
          }
          create: {
            args: Prisma.EventCreateArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$EventPayload>
          }
          createMany: {
            args: Prisma.EventCreateManyArgs<ExtArgs>
            result: BatchPayload
          }
          createManyAndReturn: {
            args: Prisma.EventCreateManyAndReturnArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$EventPayload>[]
          }
          delete: {
            args: Prisma.EventDeleteArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$EventPayload>
          }
          update: {
            args: Prisma.EventUpdateArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$EventPayload>
          }
          deleteMany: {
            args: Prisma.EventDeleteManyArgs<ExtArgs>
            result: BatchPayload
          }
          updateMany: {
            args: Prisma.EventUpdateManyArgs<ExtArgs>
            result: BatchPayload
          }
          updateManyAndReturn: {
            args: Prisma.EventUpdateManyAndReturnArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$EventPayload>[]
          }
          upsert: {
            args: Prisma.EventUpsertArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$EventPayload>
          }
          aggregate: {
            args: Prisma.EventAggregateArgs<ExtArgs>
            result: $Utils.Optional<AggregateEvent>
          }
          groupBy: {
            args: Prisma.EventGroupByArgs<ExtArgs>
            result: $Utils.Optional<EventGroupByOutputType>[]
          }
          count: {
            args: Prisma.EventCountArgs<ExtArgs>
            result: $Utils.Optional<EventCountAggregateOutputType> | number
          }
        }
      }
      Session: {
        payload: Prisma.$SessionPayload<ExtArgs>
        fields: Prisma.SessionFieldRefs
        operations: {
          findUnique: {
            args: Prisma.SessionFindUniqueArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$SessionPayload> | null
          }
          findUniqueOrThrow: {
            args: Prisma.SessionFindUniqueOrThrowArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$SessionPayload>
          }
          findFirst: {
            args: Prisma.SessionFindFirstArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$SessionPayload> | null
          }
          findFirstOrThrow: {
            args: Prisma.SessionFindFirstOrThrowArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$SessionPayload>
          }
          findMany: {
            args: Prisma.SessionFindManyArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$SessionPayload>[]
          }
          create: {
            args: Prisma.SessionCreateArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$SessionPayload>
          }
          createMany: {
            args: Prisma.SessionCreateManyArgs<ExtArgs>
            result: BatchPayload
          }
          createManyAndReturn: {
            args: Prisma.SessionCreateManyAndReturnArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$SessionPayload>[]
          }
          delete: {
            args: Prisma.SessionDeleteArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$SessionPayload>
          }
          update: {
            args: Prisma.SessionUpdateArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$SessionPayload>
          }
          deleteMany: {
            args: Prisma.SessionDeleteManyArgs<ExtArgs>
            result: BatchPayload
          }
          updateMany: {
            args: Prisma.SessionUpdateManyArgs<ExtArgs>
            result: BatchPayload
          }
          updateManyAndReturn: {
            args: Prisma.SessionUpdateManyAndReturnArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$SessionPayload>[]
          }
          upsert: {
            args: Prisma.SessionUpsertArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$SessionPayload>
          }
          aggregate: {
            args: Prisma.SessionAggregateArgs<ExtArgs>
            result: $Utils.Optional<AggregateSession>
          }
          groupBy: {
            args: Prisma.SessionGroupByArgs<ExtArgs>
            result: $Utils.Optional<SessionGroupByOutputType>[]
          }
          count: {
            args: Prisma.SessionCountArgs<ExtArgs>
            result: $Utils.Optional<SessionCountAggregateOutputType> | number
          }
        }
      }
      Ticket: {
        payload: Prisma.$TicketPayload<ExtArgs>
        fields: Prisma.TicketFieldRefs
        operations: {
          findUnique: {
            args: Prisma.TicketFindUniqueArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$TicketPayload> | null
          }
          findUniqueOrThrow: {
            args: Prisma.TicketFindUniqueOrThrowArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$TicketPayload>
          }
          findFirst: {
            args: Prisma.TicketFindFirstArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$TicketPayload> | null
          }
          findFirstOrThrow: {
            args: Prisma.TicketFindFirstOrThrowArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$TicketPayload>
          }
          findMany: {
            args: Prisma.TicketFindManyArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$TicketPayload>[]
          }
          create: {
            args: Prisma.TicketCreateArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$TicketPayload>
          }
          createMany: {
            args: Prisma.TicketCreateManyArgs<ExtArgs>
            result: BatchPayload
          }
          createManyAndReturn: {
            args: Prisma.TicketCreateManyAndReturnArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$TicketPayload>[]
          }
          delete: {
            args: Prisma.TicketDeleteArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$TicketPayload>
          }
          update: {
            args: Prisma.TicketUpdateArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$TicketPayload>
          }
          deleteMany: {
            args: Prisma.TicketDeleteManyArgs<ExtArgs>
            result: BatchPayload
          }
          updateMany: {
            args: Prisma.TicketUpdateManyArgs<ExtArgs>
            result: BatchPayload
          }
          updateManyAndReturn: {
            args: Prisma.TicketUpdateManyAndReturnArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$TicketPayload>[]
          }
          upsert: {
            args: Prisma.TicketUpsertArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$TicketPayload>
          }
          aggregate: {
            args: Prisma.TicketAggregateArgs<ExtArgs>
            result: $Utils.Optional<AggregateTicket>
          }
          groupBy: {
            args: Prisma.TicketGroupByArgs<ExtArgs>
            result: $Utils.Optional<TicketGroupByOutputType>[]
          }
          count: {
            args: Prisma.TicketCountArgs<ExtArgs>
            result: $Utils.Optional<TicketCountAggregateOutputType> | number
          }
        }
      }
      CheckInRecord: {
        payload: Prisma.$CheckInRecordPayload<ExtArgs>
        fields: Prisma.CheckInRecordFieldRefs
        operations: {
          findUnique: {
            args: Prisma.CheckInRecordFindUniqueArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$CheckInRecordPayload> | null
          }
          findUniqueOrThrow: {
            args: Prisma.CheckInRecordFindUniqueOrThrowArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$CheckInRecordPayload>
          }
          findFirst: {
            args: Prisma.CheckInRecordFindFirstArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$CheckInRecordPayload> | null
          }
          findFirstOrThrow: {
            args: Prisma.CheckInRecordFindFirstOrThrowArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$CheckInRecordPayload>
          }
          findMany: {
            args: Prisma.CheckInRecordFindManyArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$CheckInRecordPayload>[]
          }
          create: {
            args: Prisma.CheckInRecordCreateArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$CheckInRecordPayload>
          }
          createMany: {
            args: Prisma.CheckInRecordCreateManyArgs<ExtArgs>
            result: BatchPayload
          }
          createManyAndReturn: {
            args: Prisma.CheckInRecordCreateManyAndReturnArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$CheckInRecordPayload>[]
          }
          delete: {
            args: Prisma.CheckInRecordDeleteArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$CheckInRecordPayload>
          }
          update: {
            args: Prisma.CheckInRecordUpdateArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$CheckInRecordPayload>
          }
          deleteMany: {
            args: Prisma.CheckInRecordDeleteManyArgs<ExtArgs>
            result: BatchPayload
          }
          updateMany: {
            args: Prisma.CheckInRecordUpdateManyArgs<ExtArgs>
            result: BatchPayload
          }
          updateManyAndReturn: {
            args: Prisma.CheckInRecordUpdateManyAndReturnArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$CheckInRecordPayload>[]
          }
          upsert: {
            args: Prisma.CheckInRecordUpsertArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$CheckInRecordPayload>
          }
          aggregate: {
            args: Prisma.CheckInRecordAggregateArgs<ExtArgs>
            result: $Utils.Optional<AggregateCheckInRecord>
          }
          groupBy: {
            args: Prisma.CheckInRecordGroupByArgs<ExtArgs>
            result: $Utils.Optional<CheckInRecordGroupByOutputType>[]
          }
          count: {
            args: Prisma.CheckInRecordCountArgs<ExtArgs>
            result: $Utils.Optional<CheckInRecordCountAggregateOutputType> | number
          }
        }
      }
      AuditLog: {
        payload: Prisma.$AuditLogPayload<ExtArgs>
        fields: Prisma.AuditLogFieldRefs
        operations: {
          findUnique: {
            args: Prisma.AuditLogFindUniqueArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$AuditLogPayload> | null
          }
          findUniqueOrThrow: {
            args: Prisma.AuditLogFindUniqueOrThrowArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$AuditLogPayload>
          }
          findFirst: {
            args: Prisma.AuditLogFindFirstArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$AuditLogPayload> | null
          }
          findFirstOrThrow: {
            args: Prisma.AuditLogFindFirstOrThrowArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$AuditLogPayload>
          }
          findMany: {
            args: Prisma.AuditLogFindManyArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$AuditLogPayload>[]
          }
          create: {
            args: Prisma.AuditLogCreateArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$AuditLogPayload>
          }
          createMany: {
            args: Prisma.AuditLogCreateManyArgs<ExtArgs>
            result: BatchPayload
          }
          createManyAndReturn: {
            args: Prisma.AuditLogCreateManyAndReturnArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$AuditLogPayload>[]
          }
          delete: {
            args: Prisma.AuditLogDeleteArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$AuditLogPayload>
          }
          update: {
            args: Prisma.AuditLogUpdateArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$AuditLogPayload>
          }
          deleteMany: {
            args: Prisma.AuditLogDeleteManyArgs<ExtArgs>
            result: BatchPayload
          }
          updateMany: {
            args: Prisma.AuditLogUpdateManyArgs<ExtArgs>
            result: BatchPayload
          }
          updateManyAndReturn: {
            args: Prisma.AuditLogUpdateManyAndReturnArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$AuditLogPayload>[]
          }
          upsert: {
            args: Prisma.AuditLogUpsertArgs<ExtArgs>
            result: $Utils.PayloadToResult<Prisma.$AuditLogPayload>
          }
          aggregate: {
            args: Prisma.AuditLogAggregateArgs<ExtArgs>
            result: $Utils.Optional<AggregateAuditLog>
          }
          groupBy: {
            args: Prisma.AuditLogGroupByArgs<ExtArgs>
            result: $Utils.Optional<AuditLogGroupByOutputType>[]
          }
          count: {
            args: Prisma.AuditLogCountArgs<ExtArgs>
            result: $Utils.Optional<AuditLogCountAggregateOutputType> | number
          }
        }
      }
    }
  } & {
    other: {
      payload: any
      operations: {
        $executeRaw: {
          args: [query: TemplateStringsArray | Prisma.Sql, ...values: any[]],
          result: any
        }
        $executeRawUnsafe: {
          args: [query: string, ...values: any[]],
          result: any
        }
        $queryRaw: {
          args: [query: TemplateStringsArray | Prisma.Sql, ...values: any[]],
          result: any
        }
        $queryRawUnsafe: {
          args: [query: string, ...values: any[]],
          result: any
        }
      }
    }
  }
  export const defineExtension: $Extensions.ExtendsHook<"define", Prisma.TypeMapCb, $Extensions.DefaultArgs>
  export type DefaultPrismaClient = PrismaClient
  export type ErrorFormat = 'pretty' | 'colorless' | 'minimal'
  export interface PrismaClientOptions {
    /**
     * Overwrites the datasource url from your schema.prisma file
     */
    datasources?: Datasources
    /**
     * Overwrites the datasource url from your schema.prisma file
     */
    datasourceUrl?: string
    /**
     * @default "colorless"
     */
    errorFormat?: ErrorFormat
    /**
     * @example
     * ```
     * // Shorthand for `emit: 'stdout'`
     * log: ['query', 'info', 'warn', 'error']
     * 
     * // Emit as events only
     * log: [
     *   { emit: 'event', level: 'query' },
     *   { emit: 'event', level: 'info' },
     *   { emit: 'event', level: 'warn' }
     *   { emit: 'event', level: 'error' }
     * ]
     * 
     * / Emit as events and log to stdout
     * og: [
     *  { emit: 'stdout', level: 'query' },
     *  { emit: 'stdout', level: 'info' },
     *  { emit: 'stdout', level: 'warn' }
     *  { emit: 'stdout', level: 'error' }
     * 
     * ```
     * Read more in our [docs](https://www.prisma.io/docs/reference/tools-and-interfaces/prisma-client/logging#the-log-option).
     */
    log?: (LogLevel | LogDefinition)[]
    /**
     * The default values for transactionOptions
     * maxWait ?= 2000
     * timeout ?= 5000
     */
    transactionOptions?: {
      maxWait?: number
      timeout?: number
      isolationLevel?: Prisma.TransactionIsolationLevel
    }
    /**
     * Instance of a Driver Adapter, e.g., like one provided by `@prisma/adapter-planetscale`
     */
    adapter?: runtime.SqlDriverAdapterFactory | null
    /**
     * Global configuration for omitting model fields by default.
     * 
     * @example
     * ```
     * const prisma = new PrismaClient({
     *   omit: {
     *     user: {
     *       password: true
     *     }
     *   }
     * })
     * ```
     */
    omit?: Prisma.GlobalOmitConfig
  }
  export type GlobalOmitConfig = {
    adminUser?: AdminUserOmit
    family?: FamilyOmit
    parent?: ParentOmit
    child?: ChildOmit
    event?: EventOmit
    session?: SessionOmit
    ticket?: TicketOmit
    checkInRecord?: CheckInRecordOmit
    auditLog?: AuditLogOmit
  }

  /* Types for Logging */
  export type LogLevel = 'info' | 'query' | 'warn' | 'error'
  export type LogDefinition = {
    level: LogLevel
    emit: 'stdout' | 'event'
  }

  export type CheckIsLogLevel<T> = T extends LogLevel ? T : never;

  export type GetLogType<T> = CheckIsLogLevel<
    T extends LogDefinition ? T['level'] : T
  >;

  export type GetEvents<T extends any[]> = T extends Array<LogLevel | LogDefinition>
    ? GetLogType<T[number]>
    : never;

  export type QueryEvent = {
    timestamp: Date
    query: string
    params: string
    duration: number
    target: string
  }

  export type LogEvent = {
    timestamp: Date
    message: string
    target: string
  }
  /* End Types for Logging */


  export type PrismaAction =
    | 'findUnique'
    | 'findUniqueOrThrow'
    | 'findMany'
    | 'findFirst'
    | 'findFirstOrThrow'
    | 'create'
    | 'createMany'
    | 'createManyAndReturn'
    | 'update'
    | 'updateMany'
    | 'updateManyAndReturn'
    | 'upsert'
    | 'delete'
    | 'deleteMany'
    | 'executeRaw'
    | 'queryRaw'
    | 'aggregate'
    | 'count'
    | 'runCommandRaw'
    | 'findRaw'
    | 'groupBy'

  // tested in getLogLevel.test.ts
  export function getLogLevel(log: Array<LogLevel | LogDefinition>): LogLevel | undefined;

  /**
   * `PrismaClient` proxy available in interactive transactions.
   */
  export type TransactionClient = Omit<Prisma.DefaultPrismaClient, runtime.ITXClientDenyList>

  export type Datasource = {
    url?: string
  }

  /**
   * Count Types
   */


  /**
   * Count Type AdminUserCountOutputType
   */

  export type AdminUserCountOutputType = {
    checkInsPerformed: number
    checkOutsPerformed: number
  }

  export type AdminUserCountOutputTypeSelect<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    checkInsPerformed?: boolean | AdminUserCountOutputTypeCountCheckInsPerformedArgs
    checkOutsPerformed?: boolean | AdminUserCountOutputTypeCountCheckOutsPerformedArgs
  }

  // Custom InputTypes
  /**
   * AdminUserCountOutputType without action
   */
  export type AdminUserCountOutputTypeDefaultArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the AdminUserCountOutputType
     */
    select?: AdminUserCountOutputTypeSelect<ExtArgs> | null
  }

  /**
   * AdminUserCountOutputType without action
   */
  export type AdminUserCountOutputTypeCountCheckInsPerformedArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    where?: CheckInRecordWhereInput
  }

  /**
   * AdminUserCountOutputType without action
   */
  export type AdminUserCountOutputTypeCountCheckOutsPerformedArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    where?: CheckInRecordWhereInput
  }


  /**
   * Count Type FamilyCountOutputType
   */

  export type FamilyCountOutputType = {
    parents: number
    children: number
  }

  export type FamilyCountOutputTypeSelect<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    parents?: boolean | FamilyCountOutputTypeCountParentsArgs
    children?: boolean | FamilyCountOutputTypeCountChildrenArgs
  }

  // Custom InputTypes
  /**
   * FamilyCountOutputType without action
   */
  export type FamilyCountOutputTypeDefaultArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the FamilyCountOutputType
     */
    select?: FamilyCountOutputTypeSelect<ExtArgs> | null
  }

  /**
   * FamilyCountOutputType without action
   */
  export type FamilyCountOutputTypeCountParentsArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    where?: ParentWhereInput
  }

  /**
   * FamilyCountOutputType without action
   */
  export type FamilyCountOutputTypeCountChildrenArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    where?: ChildWhereInput
  }


  /**
   * Count Type ChildCountOutputType
   */

  export type ChildCountOutputType = {
    checkInRecords: number
    tickets: number
  }

  export type ChildCountOutputTypeSelect<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    checkInRecords?: boolean | ChildCountOutputTypeCountCheckInRecordsArgs
    tickets?: boolean | ChildCountOutputTypeCountTicketsArgs
  }

  // Custom InputTypes
  /**
   * ChildCountOutputType without action
   */
  export type ChildCountOutputTypeDefaultArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the ChildCountOutputType
     */
    select?: ChildCountOutputTypeSelect<ExtArgs> | null
  }

  /**
   * ChildCountOutputType without action
   */
  export type ChildCountOutputTypeCountCheckInRecordsArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    where?: CheckInRecordWhereInput
  }

  /**
   * ChildCountOutputType without action
   */
  export type ChildCountOutputTypeCountTicketsArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    where?: TicketWhereInput
  }


  /**
   * Count Type EventCountOutputType
   */

  export type EventCountOutputType = {
    sessions: number
  }

  export type EventCountOutputTypeSelect<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    sessions?: boolean | EventCountOutputTypeCountSessionsArgs
  }

  // Custom InputTypes
  /**
   * EventCountOutputType without action
   */
  export type EventCountOutputTypeDefaultArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the EventCountOutputType
     */
    select?: EventCountOutputTypeSelect<ExtArgs> | null
  }

  /**
   * EventCountOutputType without action
   */
  export type EventCountOutputTypeCountSessionsArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    where?: SessionWhereInput
  }


  /**
   * Count Type SessionCountOutputType
   */

  export type SessionCountOutputType = {
    checkInRecords: number
    tickets: number
  }

  export type SessionCountOutputTypeSelect<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    checkInRecords?: boolean | SessionCountOutputTypeCountCheckInRecordsArgs
    tickets?: boolean | SessionCountOutputTypeCountTicketsArgs
  }

  // Custom InputTypes
  /**
   * SessionCountOutputType without action
   */
  export type SessionCountOutputTypeDefaultArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the SessionCountOutputType
     */
    select?: SessionCountOutputTypeSelect<ExtArgs> | null
  }

  /**
   * SessionCountOutputType without action
   */
  export type SessionCountOutputTypeCountCheckInRecordsArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    where?: CheckInRecordWhereInput
  }

  /**
   * SessionCountOutputType without action
   */
  export type SessionCountOutputTypeCountTicketsArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    where?: TicketWhereInput
  }


  /**
   * Models
   */

  /**
   * Model AdminUser
   */

  export type AggregateAdminUser = {
    _count: AdminUserCountAggregateOutputType | null
    _min: AdminUserMinAggregateOutputType | null
    _max: AdminUserMaxAggregateOutputType | null
  }

  export type AdminUserMinAggregateOutputType = {
    id: string | null
    username: string | null
    passwordHash: string | null
    name: string | null
    createdAt: Date | null
    lastLogin: Date | null
    isActive: boolean | null
  }

  export type AdminUserMaxAggregateOutputType = {
    id: string | null
    username: string | null
    passwordHash: string | null
    name: string | null
    createdAt: Date | null
    lastLogin: Date | null
    isActive: boolean | null
  }

  export type AdminUserCountAggregateOutputType = {
    id: number
    username: number
    passwordHash: number
    name: number
    createdAt: number
    lastLogin: number
    isActive: number
    _all: number
  }


  export type AdminUserMinAggregateInputType = {
    id?: true
    username?: true
    passwordHash?: true
    name?: true
    createdAt?: true
    lastLogin?: true
    isActive?: true
  }

  export type AdminUserMaxAggregateInputType = {
    id?: true
    username?: true
    passwordHash?: true
    name?: true
    createdAt?: true
    lastLogin?: true
    isActive?: true
  }

  export type AdminUserCountAggregateInputType = {
    id?: true
    username?: true
    passwordHash?: true
    name?: true
    createdAt?: true
    lastLogin?: true
    isActive?: true
    _all?: true
  }

  export type AdminUserAggregateArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Filter which AdminUser to aggregate.
     */
    where?: AdminUserWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of AdminUsers to fetch.
     */
    orderBy?: AdminUserOrderByWithRelationInput | AdminUserOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the start position
     */
    cursor?: AdminUserWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` AdminUsers from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` AdminUsers.
     */
    skip?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/aggregations Aggregation Docs}
     * 
     * Count returned AdminUsers
    **/
    _count?: true | AdminUserCountAggregateInputType
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/aggregations Aggregation Docs}
     * 
     * Select which fields to find the minimum value
    **/
    _min?: AdminUserMinAggregateInputType
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/aggregations Aggregation Docs}
     * 
     * Select which fields to find the maximum value
    **/
    _max?: AdminUserMaxAggregateInputType
  }

  export type GetAdminUserAggregateType<T extends AdminUserAggregateArgs> = {
        [P in keyof T & keyof AggregateAdminUser]: P extends '_count' | 'count'
      ? T[P] extends true
        ? number
        : GetScalarType<T[P], AggregateAdminUser[P]>
      : GetScalarType<T[P], AggregateAdminUser[P]>
  }




  export type AdminUserGroupByArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    where?: AdminUserWhereInput
    orderBy?: AdminUserOrderByWithAggregationInput | AdminUserOrderByWithAggregationInput[]
    by: AdminUserScalarFieldEnum[] | AdminUserScalarFieldEnum
    having?: AdminUserScalarWhereWithAggregatesInput
    take?: number
    skip?: number
    _count?: AdminUserCountAggregateInputType | true
    _min?: AdminUserMinAggregateInputType
    _max?: AdminUserMaxAggregateInputType
  }

  export type AdminUserGroupByOutputType = {
    id: string
    username: string
    passwordHash: string
    name: string
    createdAt: Date
    lastLogin: Date | null
    isActive: boolean
    _count: AdminUserCountAggregateOutputType | null
    _min: AdminUserMinAggregateOutputType | null
    _max: AdminUserMaxAggregateOutputType | null
  }

  type GetAdminUserGroupByPayload<T extends AdminUserGroupByArgs> = Prisma.PrismaPromise<
    Array<
      PickEnumerable<AdminUserGroupByOutputType, T['by']> &
        {
          [P in ((keyof T) & (keyof AdminUserGroupByOutputType))]: P extends '_count'
            ? T[P] extends boolean
              ? number
              : GetScalarType<T[P], AdminUserGroupByOutputType[P]>
            : GetScalarType<T[P], AdminUserGroupByOutputType[P]>
        }
      >
    >


  export type AdminUserSelect<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetSelect<{
    id?: boolean
    username?: boolean
    passwordHash?: boolean
    name?: boolean
    createdAt?: boolean
    lastLogin?: boolean
    isActive?: boolean
    checkInsPerformed?: boolean | AdminUser$checkInsPerformedArgs<ExtArgs>
    checkOutsPerformed?: boolean | AdminUser$checkOutsPerformedArgs<ExtArgs>
    _count?: boolean | AdminUserCountOutputTypeDefaultArgs<ExtArgs>
  }, ExtArgs["result"]["adminUser"]>

  export type AdminUserSelectCreateManyAndReturn<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetSelect<{
    id?: boolean
    username?: boolean
    passwordHash?: boolean
    name?: boolean
    createdAt?: boolean
    lastLogin?: boolean
    isActive?: boolean
  }, ExtArgs["result"]["adminUser"]>

  export type AdminUserSelectUpdateManyAndReturn<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetSelect<{
    id?: boolean
    username?: boolean
    passwordHash?: boolean
    name?: boolean
    createdAt?: boolean
    lastLogin?: boolean
    isActive?: boolean
  }, ExtArgs["result"]["adminUser"]>

  export type AdminUserSelectScalar = {
    id?: boolean
    username?: boolean
    passwordHash?: boolean
    name?: boolean
    createdAt?: boolean
    lastLogin?: boolean
    isActive?: boolean
  }

  export type AdminUserOmit<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetOmit<"id" | "username" | "passwordHash" | "name" | "createdAt" | "lastLogin" | "isActive", ExtArgs["result"]["adminUser"]>
  export type AdminUserInclude<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    checkInsPerformed?: boolean | AdminUser$checkInsPerformedArgs<ExtArgs>
    checkOutsPerformed?: boolean | AdminUser$checkOutsPerformedArgs<ExtArgs>
    _count?: boolean | AdminUserCountOutputTypeDefaultArgs<ExtArgs>
  }
  export type AdminUserIncludeCreateManyAndReturn<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {}
  export type AdminUserIncludeUpdateManyAndReturn<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {}

  export type $AdminUserPayload<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    name: "AdminUser"
    objects: {
      checkInsPerformed: Prisma.$CheckInRecordPayload<ExtArgs>[]
      checkOutsPerformed: Prisma.$CheckInRecordPayload<ExtArgs>[]
    }
    scalars: $Extensions.GetPayloadResult<{
      id: string
      username: string
      passwordHash: string
      name: string
      createdAt: Date
      lastLogin: Date | null
      isActive: boolean
    }, ExtArgs["result"]["adminUser"]>
    composites: {}
  }

  type AdminUserGetPayload<S extends boolean | null | undefined | AdminUserDefaultArgs> = $Result.GetResult<Prisma.$AdminUserPayload, S>

  type AdminUserCountArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> =
    Omit<AdminUserFindManyArgs, 'select' | 'include' | 'distinct' | 'omit'> & {
      select?: AdminUserCountAggregateInputType | true
    }

  export interface AdminUserDelegate<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs, GlobalOmitOptions = {}> {
    [K: symbol]: { types: Prisma.TypeMap<ExtArgs>['model']['AdminUser'], meta: { name: 'AdminUser' } }
    /**
     * Find zero or one AdminUser that matches the filter.
     * @param {AdminUserFindUniqueArgs} args - Arguments to find a AdminUser
     * @example
     * // Get one AdminUser
     * const adminUser = await prisma.adminUser.findUnique({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findUnique<T extends AdminUserFindUniqueArgs>(args: SelectSubset<T, AdminUserFindUniqueArgs<ExtArgs>>): Prisma__AdminUserClient<$Result.GetResult<Prisma.$AdminUserPayload<ExtArgs>, T, "findUnique", GlobalOmitOptions> | null, null, ExtArgs, GlobalOmitOptions>

    /**
     * Find one AdminUser that matches the filter or throw an error with `error.code='P2025'`
     * if no matches were found.
     * @param {AdminUserFindUniqueOrThrowArgs} args - Arguments to find a AdminUser
     * @example
     * // Get one AdminUser
     * const adminUser = await prisma.adminUser.findUniqueOrThrow({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findUniqueOrThrow<T extends AdminUserFindUniqueOrThrowArgs>(args: SelectSubset<T, AdminUserFindUniqueOrThrowArgs<ExtArgs>>): Prisma__AdminUserClient<$Result.GetResult<Prisma.$AdminUserPayload<ExtArgs>, T, "findUniqueOrThrow", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Find the first AdminUser that matches the filter.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {AdminUserFindFirstArgs} args - Arguments to find a AdminUser
     * @example
     * // Get one AdminUser
     * const adminUser = await prisma.adminUser.findFirst({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findFirst<T extends AdminUserFindFirstArgs>(args?: SelectSubset<T, AdminUserFindFirstArgs<ExtArgs>>): Prisma__AdminUserClient<$Result.GetResult<Prisma.$AdminUserPayload<ExtArgs>, T, "findFirst", GlobalOmitOptions> | null, null, ExtArgs, GlobalOmitOptions>

    /**
     * Find the first AdminUser that matches the filter or
     * throw `PrismaKnownClientError` with `P2025` code if no matches were found.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {AdminUserFindFirstOrThrowArgs} args - Arguments to find a AdminUser
     * @example
     * // Get one AdminUser
     * const adminUser = await prisma.adminUser.findFirstOrThrow({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findFirstOrThrow<T extends AdminUserFindFirstOrThrowArgs>(args?: SelectSubset<T, AdminUserFindFirstOrThrowArgs<ExtArgs>>): Prisma__AdminUserClient<$Result.GetResult<Prisma.$AdminUserPayload<ExtArgs>, T, "findFirstOrThrow", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Find zero or more AdminUsers that matches the filter.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {AdminUserFindManyArgs} args - Arguments to filter and select certain fields only.
     * @example
     * // Get all AdminUsers
     * const adminUsers = await prisma.adminUser.findMany()
     * 
     * // Get first 10 AdminUsers
     * const adminUsers = await prisma.adminUser.findMany({ take: 10 })
     * 
     * // Only select the `id`
     * const adminUserWithIdOnly = await prisma.adminUser.findMany({ select: { id: true } })
     * 
     */
    findMany<T extends AdminUserFindManyArgs>(args?: SelectSubset<T, AdminUserFindManyArgs<ExtArgs>>): Prisma.PrismaPromise<$Result.GetResult<Prisma.$AdminUserPayload<ExtArgs>, T, "findMany", GlobalOmitOptions>>

    /**
     * Create a AdminUser.
     * @param {AdminUserCreateArgs} args - Arguments to create a AdminUser.
     * @example
     * // Create one AdminUser
     * const AdminUser = await prisma.adminUser.create({
     *   data: {
     *     // ... data to create a AdminUser
     *   }
     * })
     * 
     */
    create<T extends AdminUserCreateArgs>(args: SelectSubset<T, AdminUserCreateArgs<ExtArgs>>): Prisma__AdminUserClient<$Result.GetResult<Prisma.$AdminUserPayload<ExtArgs>, T, "create", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Create many AdminUsers.
     * @param {AdminUserCreateManyArgs} args - Arguments to create many AdminUsers.
     * @example
     * // Create many AdminUsers
     * const adminUser = await prisma.adminUser.createMany({
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     *     
     */
    createMany<T extends AdminUserCreateManyArgs>(args?: SelectSubset<T, AdminUserCreateManyArgs<ExtArgs>>): Prisma.PrismaPromise<BatchPayload>

    /**
     * Create many AdminUsers and returns the data saved in the database.
     * @param {AdminUserCreateManyAndReturnArgs} args - Arguments to create many AdminUsers.
     * @example
     * // Create many AdminUsers
     * const adminUser = await prisma.adminUser.createManyAndReturn({
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * 
     * // Create many AdminUsers and only return the `id`
     * const adminUserWithIdOnly = await prisma.adminUser.createManyAndReturn({
     *   select: { id: true },
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * 
     */
    createManyAndReturn<T extends AdminUserCreateManyAndReturnArgs>(args?: SelectSubset<T, AdminUserCreateManyAndReturnArgs<ExtArgs>>): Prisma.PrismaPromise<$Result.GetResult<Prisma.$AdminUserPayload<ExtArgs>, T, "createManyAndReturn", GlobalOmitOptions>>

    /**
     * Delete a AdminUser.
     * @param {AdminUserDeleteArgs} args - Arguments to delete one AdminUser.
     * @example
     * // Delete one AdminUser
     * const AdminUser = await prisma.adminUser.delete({
     *   where: {
     *     // ... filter to delete one AdminUser
     *   }
     * })
     * 
     */
    delete<T extends AdminUserDeleteArgs>(args: SelectSubset<T, AdminUserDeleteArgs<ExtArgs>>): Prisma__AdminUserClient<$Result.GetResult<Prisma.$AdminUserPayload<ExtArgs>, T, "delete", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Update one AdminUser.
     * @param {AdminUserUpdateArgs} args - Arguments to update one AdminUser.
     * @example
     * // Update one AdminUser
     * const adminUser = await prisma.adminUser.update({
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: {
     *     // ... provide data here
     *   }
     * })
     * 
     */
    update<T extends AdminUserUpdateArgs>(args: SelectSubset<T, AdminUserUpdateArgs<ExtArgs>>): Prisma__AdminUserClient<$Result.GetResult<Prisma.$AdminUserPayload<ExtArgs>, T, "update", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Delete zero or more AdminUsers.
     * @param {AdminUserDeleteManyArgs} args - Arguments to filter AdminUsers to delete.
     * @example
     * // Delete a few AdminUsers
     * const { count } = await prisma.adminUser.deleteMany({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     * 
     */
    deleteMany<T extends AdminUserDeleteManyArgs>(args?: SelectSubset<T, AdminUserDeleteManyArgs<ExtArgs>>): Prisma.PrismaPromise<BatchPayload>

    /**
     * Update zero or more AdminUsers.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {AdminUserUpdateManyArgs} args - Arguments to update one or more rows.
     * @example
     * // Update many AdminUsers
     * const adminUser = await prisma.adminUser.updateMany({
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: {
     *     // ... provide data here
     *   }
     * })
     * 
     */
    updateMany<T extends AdminUserUpdateManyArgs>(args: SelectSubset<T, AdminUserUpdateManyArgs<ExtArgs>>): Prisma.PrismaPromise<BatchPayload>

    /**
     * Update zero or more AdminUsers and returns the data updated in the database.
     * @param {AdminUserUpdateManyAndReturnArgs} args - Arguments to update many AdminUsers.
     * @example
     * // Update many AdminUsers
     * const adminUser = await prisma.adminUser.updateManyAndReturn({
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * 
     * // Update zero or more AdminUsers and only return the `id`
     * const adminUserWithIdOnly = await prisma.adminUser.updateManyAndReturn({
     *   select: { id: true },
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * 
     */
    updateManyAndReturn<T extends AdminUserUpdateManyAndReturnArgs>(args: SelectSubset<T, AdminUserUpdateManyAndReturnArgs<ExtArgs>>): Prisma.PrismaPromise<$Result.GetResult<Prisma.$AdminUserPayload<ExtArgs>, T, "updateManyAndReturn", GlobalOmitOptions>>

    /**
     * Create or update one AdminUser.
     * @param {AdminUserUpsertArgs} args - Arguments to update or create a AdminUser.
     * @example
     * // Update or create a AdminUser
     * const adminUser = await prisma.adminUser.upsert({
     *   create: {
     *     // ... data to create a AdminUser
     *   },
     *   update: {
     *     // ... in case it already exists, update
     *   },
     *   where: {
     *     // ... the filter for the AdminUser we want to update
     *   }
     * })
     */
    upsert<T extends AdminUserUpsertArgs>(args: SelectSubset<T, AdminUserUpsertArgs<ExtArgs>>): Prisma__AdminUserClient<$Result.GetResult<Prisma.$AdminUserPayload<ExtArgs>, T, "upsert", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>


    /**
     * Count the number of AdminUsers.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {AdminUserCountArgs} args - Arguments to filter AdminUsers to count.
     * @example
     * // Count the number of AdminUsers
     * const count = await prisma.adminUser.count({
     *   where: {
     *     // ... the filter for the AdminUsers we want to count
     *   }
     * })
    **/
    count<T extends AdminUserCountArgs>(
      args?: Subset<T, AdminUserCountArgs>,
    ): Prisma.PrismaPromise<
      T extends $Utils.Record<'select', any>
        ? T['select'] extends true
          ? number
          : GetScalarType<T['select'], AdminUserCountAggregateOutputType>
        : number
    >

    /**
     * Allows you to perform aggregations operations on a AdminUser.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {AdminUserAggregateArgs} args - Select which aggregations you would like to apply and on what fields.
     * @example
     * // Ordered by age ascending
     * // Where email contains prisma.io
     * // Limited to the 10 users
     * const aggregations = await prisma.user.aggregate({
     *   _avg: {
     *     age: true,
     *   },
     *   where: {
     *     email: {
     *       contains: "prisma.io",
     *     },
     *   },
     *   orderBy: {
     *     age: "asc",
     *   },
     *   take: 10,
     * })
    **/
    aggregate<T extends AdminUserAggregateArgs>(args: Subset<T, AdminUserAggregateArgs>): Prisma.PrismaPromise<GetAdminUserAggregateType<T>>

    /**
     * Group by AdminUser.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {AdminUserGroupByArgs} args - Group by arguments.
     * @example
     * // Group by city, order by createdAt, get count
     * const result = await prisma.user.groupBy({
     *   by: ['city', 'createdAt'],
     *   orderBy: {
     *     createdAt: true
     *   },
     *   _count: {
     *     _all: true
     *   },
     * })
     * 
    **/
    groupBy<
      T extends AdminUserGroupByArgs,
      HasSelectOrTake extends Or<
        Extends<'skip', Keys<T>>,
        Extends<'take', Keys<T>>
      >,
      OrderByArg extends True extends HasSelectOrTake
        ? { orderBy: AdminUserGroupByArgs['orderBy'] }
        : { orderBy?: AdminUserGroupByArgs['orderBy'] },
      OrderFields extends ExcludeUnderscoreKeys<Keys<MaybeTupleToUnion<T['orderBy']>>>,
      ByFields extends MaybeTupleToUnion<T['by']>,
      ByValid extends Has<ByFields, OrderFields>,
      HavingFields extends GetHavingFields<T['having']>,
      HavingValid extends Has<ByFields, HavingFields>,
      ByEmpty extends T['by'] extends never[] ? True : False,
      InputErrors extends ByEmpty extends True
      ? `Error: "by" must not be empty.`
      : HavingValid extends False
      ? {
          [P in HavingFields]: P extends ByFields
            ? never
            : P extends string
            ? `Error: Field "${P}" used in "having" needs to be provided in "by".`
            : [
                Error,
                'Field ',
                P,
                ` in "having" needs to be provided in "by"`,
              ]
        }[HavingFields]
      : 'take' extends Keys<T>
      ? 'orderBy' extends Keys<T>
        ? ByValid extends True
          ? {}
          : {
              [P in OrderFields]: P extends ByFields
                ? never
                : `Error: Field "${P}" in "orderBy" needs to be provided in "by"`
            }[OrderFields]
        : 'Error: If you provide "take", you also need to provide "orderBy"'
      : 'skip' extends Keys<T>
      ? 'orderBy' extends Keys<T>
        ? ByValid extends True
          ? {}
          : {
              [P in OrderFields]: P extends ByFields
                ? never
                : `Error: Field "${P}" in "orderBy" needs to be provided in "by"`
            }[OrderFields]
        : 'Error: If you provide "skip", you also need to provide "orderBy"'
      : ByValid extends True
      ? {}
      : {
          [P in OrderFields]: P extends ByFields
            ? never
            : `Error: Field "${P}" in "orderBy" needs to be provided in "by"`
        }[OrderFields]
    >(args: SubsetIntersection<T, AdminUserGroupByArgs, OrderByArg> & InputErrors): {} extends InputErrors ? GetAdminUserGroupByPayload<T> : Prisma.PrismaPromise<InputErrors>
  /**
   * Fields of the AdminUser model
   */
  readonly fields: AdminUserFieldRefs;
  }

  /**
   * The delegate class that acts as a "Promise-like" for AdminUser.
   * Why is this prefixed with `Prisma__`?
   * Because we want to prevent naming conflicts as mentioned in
   * https://github.com/prisma/prisma-client-js/issues/707
   */
  export interface Prisma__AdminUserClient<T, Null = never, ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs, GlobalOmitOptions = {}> extends Prisma.PrismaPromise<T> {
    readonly [Symbol.toStringTag]: "PrismaPromise"
    checkInsPerformed<T extends AdminUser$checkInsPerformedArgs<ExtArgs> = {}>(args?: Subset<T, AdminUser$checkInsPerformedArgs<ExtArgs>>): Prisma.PrismaPromise<$Result.GetResult<Prisma.$CheckInRecordPayload<ExtArgs>, T, "findMany", GlobalOmitOptions> | Null>
    checkOutsPerformed<T extends AdminUser$checkOutsPerformedArgs<ExtArgs> = {}>(args?: Subset<T, AdminUser$checkOutsPerformedArgs<ExtArgs>>): Prisma.PrismaPromise<$Result.GetResult<Prisma.$CheckInRecordPayload<ExtArgs>, T, "findMany", GlobalOmitOptions> | Null>
    /**
     * Attaches callbacks for the resolution and/or rejection of the Promise.
     * @param onfulfilled The callback to execute when the Promise is resolved.
     * @param onrejected The callback to execute when the Promise is rejected.
     * @returns A Promise for the completion of which ever callback is executed.
     */
    then<TResult1 = T, TResult2 = never>(onfulfilled?: ((value: T) => TResult1 | PromiseLike<TResult1>) | undefined | null, onrejected?: ((reason: any) => TResult2 | PromiseLike<TResult2>) | undefined | null): $Utils.JsPromise<TResult1 | TResult2>
    /**
     * Attaches a callback for only the rejection of the Promise.
     * @param onrejected The callback to execute when the Promise is rejected.
     * @returns A Promise for the completion of the callback.
     */
    catch<TResult = never>(onrejected?: ((reason: any) => TResult | PromiseLike<TResult>) | undefined | null): $Utils.JsPromise<T | TResult>
    /**
     * Attaches a callback that is invoked when the Promise is settled (fulfilled or rejected). The
     * resolved value cannot be modified from the callback.
     * @param onfinally The callback to execute when the Promise is settled (fulfilled or rejected).
     * @returns A Promise for the completion of the callback.
     */
    finally(onfinally?: (() => void) | undefined | null): $Utils.JsPromise<T>
  }




  /**
   * Fields of the AdminUser model
   */
  interface AdminUserFieldRefs {
    readonly id: FieldRef<"AdminUser", 'String'>
    readonly username: FieldRef<"AdminUser", 'String'>
    readonly passwordHash: FieldRef<"AdminUser", 'String'>
    readonly name: FieldRef<"AdminUser", 'String'>
    readonly createdAt: FieldRef<"AdminUser", 'DateTime'>
    readonly lastLogin: FieldRef<"AdminUser", 'DateTime'>
    readonly isActive: FieldRef<"AdminUser", 'Boolean'>
  }
    

  // Custom InputTypes
  /**
   * AdminUser findUnique
   */
  export type AdminUserFindUniqueArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the AdminUser
     */
    select?: AdminUserSelect<ExtArgs> | null
    /**
     * Omit specific fields from the AdminUser
     */
    omit?: AdminUserOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: AdminUserInclude<ExtArgs> | null
    /**
     * Filter, which AdminUser to fetch.
     */
    where: AdminUserWhereUniqueInput
  }

  /**
   * AdminUser findUniqueOrThrow
   */
  export type AdminUserFindUniqueOrThrowArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the AdminUser
     */
    select?: AdminUserSelect<ExtArgs> | null
    /**
     * Omit specific fields from the AdminUser
     */
    omit?: AdminUserOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: AdminUserInclude<ExtArgs> | null
    /**
     * Filter, which AdminUser to fetch.
     */
    where: AdminUserWhereUniqueInput
  }

  /**
   * AdminUser findFirst
   */
  export type AdminUserFindFirstArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the AdminUser
     */
    select?: AdminUserSelect<ExtArgs> | null
    /**
     * Omit specific fields from the AdminUser
     */
    omit?: AdminUserOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: AdminUserInclude<ExtArgs> | null
    /**
     * Filter, which AdminUser to fetch.
     */
    where?: AdminUserWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of AdminUsers to fetch.
     */
    orderBy?: AdminUserOrderByWithRelationInput | AdminUserOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the position for searching for AdminUsers.
     */
    cursor?: AdminUserWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` AdminUsers from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` AdminUsers.
     */
    skip?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/distinct Distinct Docs}
     * 
     * Filter by unique combinations of AdminUsers.
     */
    distinct?: AdminUserScalarFieldEnum | AdminUserScalarFieldEnum[]
  }

  /**
   * AdminUser findFirstOrThrow
   */
  export type AdminUserFindFirstOrThrowArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the AdminUser
     */
    select?: AdminUserSelect<ExtArgs> | null
    /**
     * Omit specific fields from the AdminUser
     */
    omit?: AdminUserOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: AdminUserInclude<ExtArgs> | null
    /**
     * Filter, which AdminUser to fetch.
     */
    where?: AdminUserWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of AdminUsers to fetch.
     */
    orderBy?: AdminUserOrderByWithRelationInput | AdminUserOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the position for searching for AdminUsers.
     */
    cursor?: AdminUserWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` AdminUsers from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` AdminUsers.
     */
    skip?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/distinct Distinct Docs}
     * 
     * Filter by unique combinations of AdminUsers.
     */
    distinct?: AdminUserScalarFieldEnum | AdminUserScalarFieldEnum[]
  }

  /**
   * AdminUser findMany
   */
  export type AdminUserFindManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the AdminUser
     */
    select?: AdminUserSelect<ExtArgs> | null
    /**
     * Omit specific fields from the AdminUser
     */
    omit?: AdminUserOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: AdminUserInclude<ExtArgs> | null
    /**
     * Filter, which AdminUsers to fetch.
     */
    where?: AdminUserWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of AdminUsers to fetch.
     */
    orderBy?: AdminUserOrderByWithRelationInput | AdminUserOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the position for listing AdminUsers.
     */
    cursor?: AdminUserWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` AdminUsers from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` AdminUsers.
     */
    skip?: number
    distinct?: AdminUserScalarFieldEnum | AdminUserScalarFieldEnum[]
  }

  /**
   * AdminUser create
   */
  export type AdminUserCreateArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the AdminUser
     */
    select?: AdminUserSelect<ExtArgs> | null
    /**
     * Omit specific fields from the AdminUser
     */
    omit?: AdminUserOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: AdminUserInclude<ExtArgs> | null
    /**
     * The data needed to create a AdminUser.
     */
    data: XOR<AdminUserCreateInput, AdminUserUncheckedCreateInput>
  }

  /**
   * AdminUser createMany
   */
  export type AdminUserCreateManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * The data used to create many AdminUsers.
     */
    data: AdminUserCreateManyInput | AdminUserCreateManyInput[]
    skipDuplicates?: boolean
  }

  /**
   * AdminUser createManyAndReturn
   */
  export type AdminUserCreateManyAndReturnArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the AdminUser
     */
    select?: AdminUserSelectCreateManyAndReturn<ExtArgs> | null
    /**
     * Omit specific fields from the AdminUser
     */
    omit?: AdminUserOmit<ExtArgs> | null
    /**
     * The data used to create many AdminUsers.
     */
    data: AdminUserCreateManyInput | AdminUserCreateManyInput[]
    skipDuplicates?: boolean
  }

  /**
   * AdminUser update
   */
  export type AdminUserUpdateArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the AdminUser
     */
    select?: AdminUserSelect<ExtArgs> | null
    /**
     * Omit specific fields from the AdminUser
     */
    omit?: AdminUserOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: AdminUserInclude<ExtArgs> | null
    /**
     * The data needed to update a AdminUser.
     */
    data: XOR<AdminUserUpdateInput, AdminUserUncheckedUpdateInput>
    /**
     * Choose, which AdminUser to update.
     */
    where: AdminUserWhereUniqueInput
  }

  /**
   * AdminUser updateMany
   */
  export type AdminUserUpdateManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * The data used to update AdminUsers.
     */
    data: XOR<AdminUserUpdateManyMutationInput, AdminUserUncheckedUpdateManyInput>
    /**
     * Filter which AdminUsers to update
     */
    where?: AdminUserWhereInput
    /**
     * Limit how many AdminUsers to update.
     */
    limit?: number
  }

  /**
   * AdminUser updateManyAndReturn
   */
  export type AdminUserUpdateManyAndReturnArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the AdminUser
     */
    select?: AdminUserSelectUpdateManyAndReturn<ExtArgs> | null
    /**
     * Omit specific fields from the AdminUser
     */
    omit?: AdminUserOmit<ExtArgs> | null
    /**
     * The data used to update AdminUsers.
     */
    data: XOR<AdminUserUpdateManyMutationInput, AdminUserUncheckedUpdateManyInput>
    /**
     * Filter which AdminUsers to update
     */
    where?: AdminUserWhereInput
    /**
     * Limit how many AdminUsers to update.
     */
    limit?: number
  }

  /**
   * AdminUser upsert
   */
  export type AdminUserUpsertArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the AdminUser
     */
    select?: AdminUserSelect<ExtArgs> | null
    /**
     * Omit specific fields from the AdminUser
     */
    omit?: AdminUserOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: AdminUserInclude<ExtArgs> | null
    /**
     * The filter to search for the AdminUser to update in case it exists.
     */
    where: AdminUserWhereUniqueInput
    /**
     * In case the AdminUser found by the `where` argument doesn't exist, create a new AdminUser with this data.
     */
    create: XOR<AdminUserCreateInput, AdminUserUncheckedCreateInput>
    /**
     * In case the AdminUser was found with the provided `where` argument, update it with this data.
     */
    update: XOR<AdminUserUpdateInput, AdminUserUncheckedUpdateInput>
  }

  /**
   * AdminUser delete
   */
  export type AdminUserDeleteArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the AdminUser
     */
    select?: AdminUserSelect<ExtArgs> | null
    /**
     * Omit specific fields from the AdminUser
     */
    omit?: AdminUserOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: AdminUserInclude<ExtArgs> | null
    /**
     * Filter which AdminUser to delete.
     */
    where: AdminUserWhereUniqueInput
  }

  /**
   * AdminUser deleteMany
   */
  export type AdminUserDeleteManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Filter which AdminUsers to delete
     */
    where?: AdminUserWhereInput
    /**
     * Limit how many AdminUsers to delete.
     */
    limit?: number
  }

  /**
   * AdminUser.checkInsPerformed
   */
  export type AdminUser$checkInsPerformedArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the CheckInRecord
     */
    select?: CheckInRecordSelect<ExtArgs> | null
    /**
     * Omit specific fields from the CheckInRecord
     */
    omit?: CheckInRecordOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: CheckInRecordInclude<ExtArgs> | null
    where?: CheckInRecordWhereInput
    orderBy?: CheckInRecordOrderByWithRelationInput | CheckInRecordOrderByWithRelationInput[]
    cursor?: CheckInRecordWhereUniqueInput
    take?: number
    skip?: number
    distinct?: CheckInRecordScalarFieldEnum | CheckInRecordScalarFieldEnum[]
  }

  /**
   * AdminUser.checkOutsPerformed
   */
  export type AdminUser$checkOutsPerformedArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the CheckInRecord
     */
    select?: CheckInRecordSelect<ExtArgs> | null
    /**
     * Omit specific fields from the CheckInRecord
     */
    omit?: CheckInRecordOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: CheckInRecordInclude<ExtArgs> | null
    where?: CheckInRecordWhereInput
    orderBy?: CheckInRecordOrderByWithRelationInput | CheckInRecordOrderByWithRelationInput[]
    cursor?: CheckInRecordWhereUniqueInput
    take?: number
    skip?: number
    distinct?: CheckInRecordScalarFieldEnum | CheckInRecordScalarFieldEnum[]
  }

  /**
   * AdminUser without action
   */
  export type AdminUserDefaultArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the AdminUser
     */
    select?: AdminUserSelect<ExtArgs> | null
    /**
     * Omit specific fields from the AdminUser
     */
    omit?: AdminUserOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: AdminUserInclude<ExtArgs> | null
  }


  /**
   * Model Family
   */

  export type AggregateFamily = {
    _count: FamilyCountAggregateOutputType | null
    _min: FamilyMinAggregateOutputType | null
    _max: FamilyMaxAggregateOutputType | null
  }

  export type FamilyMinAggregateOutputType = {
    id: string | null
    lastParticipationDate: Date | null
  }

  export type FamilyMaxAggregateOutputType = {
    id: string | null
    lastParticipationDate: Date | null
  }

  export type FamilyCountAggregateOutputType = {
    id: number
    lastParticipationDate: number
    _all: number
  }


  export type FamilyMinAggregateInputType = {
    id?: true
    lastParticipationDate?: true
  }

  export type FamilyMaxAggregateInputType = {
    id?: true
    lastParticipationDate?: true
  }

  export type FamilyCountAggregateInputType = {
    id?: true
    lastParticipationDate?: true
    _all?: true
  }

  export type FamilyAggregateArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Filter which Family to aggregate.
     */
    where?: FamilyWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of Families to fetch.
     */
    orderBy?: FamilyOrderByWithRelationInput | FamilyOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the start position
     */
    cursor?: FamilyWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` Families from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` Families.
     */
    skip?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/aggregations Aggregation Docs}
     * 
     * Count returned Families
    **/
    _count?: true | FamilyCountAggregateInputType
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/aggregations Aggregation Docs}
     * 
     * Select which fields to find the minimum value
    **/
    _min?: FamilyMinAggregateInputType
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/aggregations Aggregation Docs}
     * 
     * Select which fields to find the maximum value
    **/
    _max?: FamilyMaxAggregateInputType
  }

  export type GetFamilyAggregateType<T extends FamilyAggregateArgs> = {
        [P in keyof T & keyof AggregateFamily]: P extends '_count' | 'count'
      ? T[P] extends true
        ? number
        : GetScalarType<T[P], AggregateFamily[P]>
      : GetScalarType<T[P], AggregateFamily[P]>
  }




  export type FamilyGroupByArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    where?: FamilyWhereInput
    orderBy?: FamilyOrderByWithAggregationInput | FamilyOrderByWithAggregationInput[]
    by: FamilyScalarFieldEnum[] | FamilyScalarFieldEnum
    having?: FamilyScalarWhereWithAggregatesInput
    take?: number
    skip?: number
    _count?: FamilyCountAggregateInputType | true
    _min?: FamilyMinAggregateInputType
    _max?: FamilyMaxAggregateInputType
  }

  export type FamilyGroupByOutputType = {
    id: string
    lastParticipationDate: Date | null
    _count: FamilyCountAggregateOutputType | null
    _min: FamilyMinAggregateOutputType | null
    _max: FamilyMaxAggregateOutputType | null
  }

  type GetFamilyGroupByPayload<T extends FamilyGroupByArgs> = Prisma.PrismaPromise<
    Array<
      PickEnumerable<FamilyGroupByOutputType, T['by']> &
        {
          [P in ((keyof T) & (keyof FamilyGroupByOutputType))]: P extends '_count'
            ? T[P] extends boolean
              ? number
              : GetScalarType<T[P], FamilyGroupByOutputType[P]>
            : GetScalarType<T[P], FamilyGroupByOutputType[P]>
        }
      >
    >


  export type FamilySelect<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetSelect<{
    id?: boolean
    lastParticipationDate?: boolean
    parents?: boolean | Family$parentsArgs<ExtArgs>
    children?: boolean | Family$childrenArgs<ExtArgs>
    _count?: boolean | FamilyCountOutputTypeDefaultArgs<ExtArgs>
  }, ExtArgs["result"]["family"]>

  export type FamilySelectCreateManyAndReturn<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetSelect<{
    id?: boolean
    lastParticipationDate?: boolean
  }, ExtArgs["result"]["family"]>

  export type FamilySelectUpdateManyAndReturn<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetSelect<{
    id?: boolean
    lastParticipationDate?: boolean
  }, ExtArgs["result"]["family"]>

  export type FamilySelectScalar = {
    id?: boolean
    lastParticipationDate?: boolean
  }

  export type FamilyOmit<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetOmit<"id" | "lastParticipationDate", ExtArgs["result"]["family"]>
  export type FamilyInclude<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    parents?: boolean | Family$parentsArgs<ExtArgs>
    children?: boolean | Family$childrenArgs<ExtArgs>
    _count?: boolean | FamilyCountOutputTypeDefaultArgs<ExtArgs>
  }
  export type FamilyIncludeCreateManyAndReturn<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {}
  export type FamilyIncludeUpdateManyAndReturn<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {}

  export type $FamilyPayload<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    name: "Family"
    objects: {
      parents: Prisma.$ParentPayload<ExtArgs>[]
      children: Prisma.$ChildPayload<ExtArgs>[]
    }
    scalars: $Extensions.GetPayloadResult<{
      id: string
      lastParticipationDate: Date | null
    }, ExtArgs["result"]["family"]>
    composites: {}
  }

  type FamilyGetPayload<S extends boolean | null | undefined | FamilyDefaultArgs> = $Result.GetResult<Prisma.$FamilyPayload, S>

  type FamilyCountArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> =
    Omit<FamilyFindManyArgs, 'select' | 'include' | 'distinct' | 'omit'> & {
      select?: FamilyCountAggregateInputType | true
    }

  export interface FamilyDelegate<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs, GlobalOmitOptions = {}> {
    [K: symbol]: { types: Prisma.TypeMap<ExtArgs>['model']['Family'], meta: { name: 'Family' } }
    /**
     * Find zero or one Family that matches the filter.
     * @param {FamilyFindUniqueArgs} args - Arguments to find a Family
     * @example
     * // Get one Family
     * const family = await prisma.family.findUnique({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findUnique<T extends FamilyFindUniqueArgs>(args: SelectSubset<T, FamilyFindUniqueArgs<ExtArgs>>): Prisma__FamilyClient<$Result.GetResult<Prisma.$FamilyPayload<ExtArgs>, T, "findUnique", GlobalOmitOptions> | null, null, ExtArgs, GlobalOmitOptions>

    /**
     * Find one Family that matches the filter or throw an error with `error.code='P2025'`
     * if no matches were found.
     * @param {FamilyFindUniqueOrThrowArgs} args - Arguments to find a Family
     * @example
     * // Get one Family
     * const family = await prisma.family.findUniqueOrThrow({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findUniqueOrThrow<T extends FamilyFindUniqueOrThrowArgs>(args: SelectSubset<T, FamilyFindUniqueOrThrowArgs<ExtArgs>>): Prisma__FamilyClient<$Result.GetResult<Prisma.$FamilyPayload<ExtArgs>, T, "findUniqueOrThrow", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Find the first Family that matches the filter.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {FamilyFindFirstArgs} args - Arguments to find a Family
     * @example
     * // Get one Family
     * const family = await prisma.family.findFirst({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findFirst<T extends FamilyFindFirstArgs>(args?: SelectSubset<T, FamilyFindFirstArgs<ExtArgs>>): Prisma__FamilyClient<$Result.GetResult<Prisma.$FamilyPayload<ExtArgs>, T, "findFirst", GlobalOmitOptions> | null, null, ExtArgs, GlobalOmitOptions>

    /**
     * Find the first Family that matches the filter or
     * throw `PrismaKnownClientError` with `P2025` code if no matches were found.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {FamilyFindFirstOrThrowArgs} args - Arguments to find a Family
     * @example
     * // Get one Family
     * const family = await prisma.family.findFirstOrThrow({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findFirstOrThrow<T extends FamilyFindFirstOrThrowArgs>(args?: SelectSubset<T, FamilyFindFirstOrThrowArgs<ExtArgs>>): Prisma__FamilyClient<$Result.GetResult<Prisma.$FamilyPayload<ExtArgs>, T, "findFirstOrThrow", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Find zero or more Families that matches the filter.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {FamilyFindManyArgs} args - Arguments to filter and select certain fields only.
     * @example
     * // Get all Families
     * const families = await prisma.family.findMany()
     * 
     * // Get first 10 Families
     * const families = await prisma.family.findMany({ take: 10 })
     * 
     * // Only select the `id`
     * const familyWithIdOnly = await prisma.family.findMany({ select: { id: true } })
     * 
     */
    findMany<T extends FamilyFindManyArgs>(args?: SelectSubset<T, FamilyFindManyArgs<ExtArgs>>): Prisma.PrismaPromise<$Result.GetResult<Prisma.$FamilyPayload<ExtArgs>, T, "findMany", GlobalOmitOptions>>

    /**
     * Create a Family.
     * @param {FamilyCreateArgs} args - Arguments to create a Family.
     * @example
     * // Create one Family
     * const Family = await prisma.family.create({
     *   data: {
     *     // ... data to create a Family
     *   }
     * })
     * 
     */
    create<T extends FamilyCreateArgs>(args: SelectSubset<T, FamilyCreateArgs<ExtArgs>>): Prisma__FamilyClient<$Result.GetResult<Prisma.$FamilyPayload<ExtArgs>, T, "create", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Create many Families.
     * @param {FamilyCreateManyArgs} args - Arguments to create many Families.
     * @example
     * // Create many Families
     * const family = await prisma.family.createMany({
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     *     
     */
    createMany<T extends FamilyCreateManyArgs>(args?: SelectSubset<T, FamilyCreateManyArgs<ExtArgs>>): Prisma.PrismaPromise<BatchPayload>

    /**
     * Create many Families and returns the data saved in the database.
     * @param {FamilyCreateManyAndReturnArgs} args - Arguments to create many Families.
     * @example
     * // Create many Families
     * const family = await prisma.family.createManyAndReturn({
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * 
     * // Create many Families and only return the `id`
     * const familyWithIdOnly = await prisma.family.createManyAndReturn({
     *   select: { id: true },
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * 
     */
    createManyAndReturn<T extends FamilyCreateManyAndReturnArgs>(args?: SelectSubset<T, FamilyCreateManyAndReturnArgs<ExtArgs>>): Prisma.PrismaPromise<$Result.GetResult<Prisma.$FamilyPayload<ExtArgs>, T, "createManyAndReturn", GlobalOmitOptions>>

    /**
     * Delete a Family.
     * @param {FamilyDeleteArgs} args - Arguments to delete one Family.
     * @example
     * // Delete one Family
     * const Family = await prisma.family.delete({
     *   where: {
     *     // ... filter to delete one Family
     *   }
     * })
     * 
     */
    delete<T extends FamilyDeleteArgs>(args: SelectSubset<T, FamilyDeleteArgs<ExtArgs>>): Prisma__FamilyClient<$Result.GetResult<Prisma.$FamilyPayload<ExtArgs>, T, "delete", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Update one Family.
     * @param {FamilyUpdateArgs} args - Arguments to update one Family.
     * @example
     * // Update one Family
     * const family = await prisma.family.update({
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: {
     *     // ... provide data here
     *   }
     * })
     * 
     */
    update<T extends FamilyUpdateArgs>(args: SelectSubset<T, FamilyUpdateArgs<ExtArgs>>): Prisma__FamilyClient<$Result.GetResult<Prisma.$FamilyPayload<ExtArgs>, T, "update", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Delete zero or more Families.
     * @param {FamilyDeleteManyArgs} args - Arguments to filter Families to delete.
     * @example
     * // Delete a few Families
     * const { count } = await prisma.family.deleteMany({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     * 
     */
    deleteMany<T extends FamilyDeleteManyArgs>(args?: SelectSubset<T, FamilyDeleteManyArgs<ExtArgs>>): Prisma.PrismaPromise<BatchPayload>

    /**
     * Update zero or more Families.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {FamilyUpdateManyArgs} args - Arguments to update one or more rows.
     * @example
     * // Update many Families
     * const family = await prisma.family.updateMany({
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: {
     *     // ... provide data here
     *   }
     * })
     * 
     */
    updateMany<T extends FamilyUpdateManyArgs>(args: SelectSubset<T, FamilyUpdateManyArgs<ExtArgs>>): Prisma.PrismaPromise<BatchPayload>

    /**
     * Update zero or more Families and returns the data updated in the database.
     * @param {FamilyUpdateManyAndReturnArgs} args - Arguments to update many Families.
     * @example
     * // Update many Families
     * const family = await prisma.family.updateManyAndReturn({
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * 
     * // Update zero or more Families and only return the `id`
     * const familyWithIdOnly = await prisma.family.updateManyAndReturn({
     *   select: { id: true },
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * 
     */
    updateManyAndReturn<T extends FamilyUpdateManyAndReturnArgs>(args: SelectSubset<T, FamilyUpdateManyAndReturnArgs<ExtArgs>>): Prisma.PrismaPromise<$Result.GetResult<Prisma.$FamilyPayload<ExtArgs>, T, "updateManyAndReturn", GlobalOmitOptions>>

    /**
     * Create or update one Family.
     * @param {FamilyUpsertArgs} args - Arguments to update or create a Family.
     * @example
     * // Update or create a Family
     * const family = await prisma.family.upsert({
     *   create: {
     *     // ... data to create a Family
     *   },
     *   update: {
     *     // ... in case it already exists, update
     *   },
     *   where: {
     *     // ... the filter for the Family we want to update
     *   }
     * })
     */
    upsert<T extends FamilyUpsertArgs>(args: SelectSubset<T, FamilyUpsertArgs<ExtArgs>>): Prisma__FamilyClient<$Result.GetResult<Prisma.$FamilyPayload<ExtArgs>, T, "upsert", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>


    /**
     * Count the number of Families.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {FamilyCountArgs} args - Arguments to filter Families to count.
     * @example
     * // Count the number of Families
     * const count = await prisma.family.count({
     *   where: {
     *     // ... the filter for the Families we want to count
     *   }
     * })
    **/
    count<T extends FamilyCountArgs>(
      args?: Subset<T, FamilyCountArgs>,
    ): Prisma.PrismaPromise<
      T extends $Utils.Record<'select', any>
        ? T['select'] extends true
          ? number
          : GetScalarType<T['select'], FamilyCountAggregateOutputType>
        : number
    >

    /**
     * Allows you to perform aggregations operations on a Family.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {FamilyAggregateArgs} args - Select which aggregations you would like to apply and on what fields.
     * @example
     * // Ordered by age ascending
     * // Where email contains prisma.io
     * // Limited to the 10 users
     * const aggregations = await prisma.user.aggregate({
     *   _avg: {
     *     age: true,
     *   },
     *   where: {
     *     email: {
     *       contains: "prisma.io",
     *     },
     *   },
     *   orderBy: {
     *     age: "asc",
     *   },
     *   take: 10,
     * })
    **/
    aggregate<T extends FamilyAggregateArgs>(args: Subset<T, FamilyAggregateArgs>): Prisma.PrismaPromise<GetFamilyAggregateType<T>>

    /**
     * Group by Family.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {FamilyGroupByArgs} args - Group by arguments.
     * @example
     * // Group by city, order by createdAt, get count
     * const result = await prisma.user.groupBy({
     *   by: ['city', 'createdAt'],
     *   orderBy: {
     *     createdAt: true
     *   },
     *   _count: {
     *     _all: true
     *   },
     * })
     * 
    **/
    groupBy<
      T extends FamilyGroupByArgs,
      HasSelectOrTake extends Or<
        Extends<'skip', Keys<T>>,
        Extends<'take', Keys<T>>
      >,
      OrderByArg extends True extends HasSelectOrTake
        ? { orderBy: FamilyGroupByArgs['orderBy'] }
        : { orderBy?: FamilyGroupByArgs['orderBy'] },
      OrderFields extends ExcludeUnderscoreKeys<Keys<MaybeTupleToUnion<T['orderBy']>>>,
      ByFields extends MaybeTupleToUnion<T['by']>,
      ByValid extends Has<ByFields, OrderFields>,
      HavingFields extends GetHavingFields<T['having']>,
      HavingValid extends Has<ByFields, HavingFields>,
      ByEmpty extends T['by'] extends never[] ? True : False,
      InputErrors extends ByEmpty extends True
      ? `Error: "by" must not be empty.`
      : HavingValid extends False
      ? {
          [P in HavingFields]: P extends ByFields
            ? never
            : P extends string
            ? `Error: Field "${P}" used in "having" needs to be provided in "by".`
            : [
                Error,
                'Field ',
                P,
                ` in "having" needs to be provided in "by"`,
              ]
        }[HavingFields]
      : 'take' extends Keys<T>
      ? 'orderBy' extends Keys<T>
        ? ByValid extends True
          ? {}
          : {
              [P in OrderFields]: P extends ByFields
                ? never
                : `Error: Field "${P}" in "orderBy" needs to be provided in "by"`
            }[OrderFields]
        : 'Error: If you provide "take", you also need to provide "orderBy"'
      : 'skip' extends Keys<T>
      ? 'orderBy' extends Keys<T>
        ? ByValid extends True
          ? {}
          : {
              [P in OrderFields]: P extends ByFields
                ? never
                : `Error: Field "${P}" in "orderBy" needs to be provided in "by"`
            }[OrderFields]
        : 'Error: If you provide "skip", you also need to provide "orderBy"'
      : ByValid extends True
      ? {}
      : {
          [P in OrderFields]: P extends ByFields
            ? never
            : `Error: Field "${P}" in "orderBy" needs to be provided in "by"`
        }[OrderFields]
    >(args: SubsetIntersection<T, FamilyGroupByArgs, OrderByArg> & InputErrors): {} extends InputErrors ? GetFamilyGroupByPayload<T> : Prisma.PrismaPromise<InputErrors>
  /**
   * Fields of the Family model
   */
  readonly fields: FamilyFieldRefs;
  }

  /**
   * The delegate class that acts as a "Promise-like" for Family.
   * Why is this prefixed with `Prisma__`?
   * Because we want to prevent naming conflicts as mentioned in
   * https://github.com/prisma/prisma-client-js/issues/707
   */
  export interface Prisma__FamilyClient<T, Null = never, ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs, GlobalOmitOptions = {}> extends Prisma.PrismaPromise<T> {
    readonly [Symbol.toStringTag]: "PrismaPromise"
    parents<T extends Family$parentsArgs<ExtArgs> = {}>(args?: Subset<T, Family$parentsArgs<ExtArgs>>): Prisma.PrismaPromise<$Result.GetResult<Prisma.$ParentPayload<ExtArgs>, T, "findMany", GlobalOmitOptions> | Null>
    children<T extends Family$childrenArgs<ExtArgs> = {}>(args?: Subset<T, Family$childrenArgs<ExtArgs>>): Prisma.PrismaPromise<$Result.GetResult<Prisma.$ChildPayload<ExtArgs>, T, "findMany", GlobalOmitOptions> | Null>
    /**
     * Attaches callbacks for the resolution and/or rejection of the Promise.
     * @param onfulfilled The callback to execute when the Promise is resolved.
     * @param onrejected The callback to execute when the Promise is rejected.
     * @returns A Promise for the completion of which ever callback is executed.
     */
    then<TResult1 = T, TResult2 = never>(onfulfilled?: ((value: T) => TResult1 | PromiseLike<TResult1>) | undefined | null, onrejected?: ((reason: any) => TResult2 | PromiseLike<TResult2>) | undefined | null): $Utils.JsPromise<TResult1 | TResult2>
    /**
     * Attaches a callback for only the rejection of the Promise.
     * @param onrejected The callback to execute when the Promise is rejected.
     * @returns A Promise for the completion of the callback.
     */
    catch<TResult = never>(onrejected?: ((reason: any) => TResult | PromiseLike<TResult>) | undefined | null): $Utils.JsPromise<T | TResult>
    /**
     * Attaches a callback that is invoked when the Promise is settled (fulfilled or rejected). The
     * resolved value cannot be modified from the callback.
     * @param onfinally The callback to execute when the Promise is settled (fulfilled or rejected).
     * @returns A Promise for the completion of the callback.
     */
    finally(onfinally?: (() => void) | undefined | null): $Utils.JsPromise<T>
  }




  /**
   * Fields of the Family model
   */
  interface FamilyFieldRefs {
    readonly id: FieldRef<"Family", 'String'>
    readonly lastParticipationDate: FieldRef<"Family", 'DateTime'>
  }
    

  // Custom InputTypes
  /**
   * Family findUnique
   */
  export type FamilyFindUniqueArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Family
     */
    select?: FamilySelect<ExtArgs> | null
    /**
     * Omit specific fields from the Family
     */
    omit?: FamilyOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: FamilyInclude<ExtArgs> | null
    /**
     * Filter, which Family to fetch.
     */
    where: FamilyWhereUniqueInput
  }

  /**
   * Family findUniqueOrThrow
   */
  export type FamilyFindUniqueOrThrowArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Family
     */
    select?: FamilySelect<ExtArgs> | null
    /**
     * Omit specific fields from the Family
     */
    omit?: FamilyOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: FamilyInclude<ExtArgs> | null
    /**
     * Filter, which Family to fetch.
     */
    where: FamilyWhereUniqueInput
  }

  /**
   * Family findFirst
   */
  export type FamilyFindFirstArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Family
     */
    select?: FamilySelect<ExtArgs> | null
    /**
     * Omit specific fields from the Family
     */
    omit?: FamilyOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: FamilyInclude<ExtArgs> | null
    /**
     * Filter, which Family to fetch.
     */
    where?: FamilyWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of Families to fetch.
     */
    orderBy?: FamilyOrderByWithRelationInput | FamilyOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the position for searching for Families.
     */
    cursor?: FamilyWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` Families from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` Families.
     */
    skip?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/distinct Distinct Docs}
     * 
     * Filter by unique combinations of Families.
     */
    distinct?: FamilyScalarFieldEnum | FamilyScalarFieldEnum[]
  }

  /**
   * Family findFirstOrThrow
   */
  export type FamilyFindFirstOrThrowArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Family
     */
    select?: FamilySelect<ExtArgs> | null
    /**
     * Omit specific fields from the Family
     */
    omit?: FamilyOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: FamilyInclude<ExtArgs> | null
    /**
     * Filter, which Family to fetch.
     */
    where?: FamilyWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of Families to fetch.
     */
    orderBy?: FamilyOrderByWithRelationInput | FamilyOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the position for searching for Families.
     */
    cursor?: FamilyWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` Families from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` Families.
     */
    skip?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/distinct Distinct Docs}
     * 
     * Filter by unique combinations of Families.
     */
    distinct?: FamilyScalarFieldEnum | FamilyScalarFieldEnum[]
  }

  /**
   * Family findMany
   */
  export type FamilyFindManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Family
     */
    select?: FamilySelect<ExtArgs> | null
    /**
     * Omit specific fields from the Family
     */
    omit?: FamilyOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: FamilyInclude<ExtArgs> | null
    /**
     * Filter, which Families to fetch.
     */
    where?: FamilyWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of Families to fetch.
     */
    orderBy?: FamilyOrderByWithRelationInput | FamilyOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the position for listing Families.
     */
    cursor?: FamilyWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` Families from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` Families.
     */
    skip?: number
    distinct?: FamilyScalarFieldEnum | FamilyScalarFieldEnum[]
  }

  /**
   * Family create
   */
  export type FamilyCreateArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Family
     */
    select?: FamilySelect<ExtArgs> | null
    /**
     * Omit specific fields from the Family
     */
    omit?: FamilyOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: FamilyInclude<ExtArgs> | null
    /**
     * The data needed to create a Family.
     */
    data?: XOR<FamilyCreateInput, FamilyUncheckedCreateInput>
  }

  /**
   * Family createMany
   */
  export type FamilyCreateManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * The data used to create many Families.
     */
    data: FamilyCreateManyInput | FamilyCreateManyInput[]
    skipDuplicates?: boolean
  }

  /**
   * Family createManyAndReturn
   */
  export type FamilyCreateManyAndReturnArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Family
     */
    select?: FamilySelectCreateManyAndReturn<ExtArgs> | null
    /**
     * Omit specific fields from the Family
     */
    omit?: FamilyOmit<ExtArgs> | null
    /**
     * The data used to create many Families.
     */
    data: FamilyCreateManyInput | FamilyCreateManyInput[]
    skipDuplicates?: boolean
  }

  /**
   * Family update
   */
  export type FamilyUpdateArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Family
     */
    select?: FamilySelect<ExtArgs> | null
    /**
     * Omit specific fields from the Family
     */
    omit?: FamilyOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: FamilyInclude<ExtArgs> | null
    /**
     * The data needed to update a Family.
     */
    data: XOR<FamilyUpdateInput, FamilyUncheckedUpdateInput>
    /**
     * Choose, which Family to update.
     */
    where: FamilyWhereUniqueInput
  }

  /**
   * Family updateMany
   */
  export type FamilyUpdateManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * The data used to update Families.
     */
    data: XOR<FamilyUpdateManyMutationInput, FamilyUncheckedUpdateManyInput>
    /**
     * Filter which Families to update
     */
    where?: FamilyWhereInput
    /**
     * Limit how many Families to update.
     */
    limit?: number
  }

  /**
   * Family updateManyAndReturn
   */
  export type FamilyUpdateManyAndReturnArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Family
     */
    select?: FamilySelectUpdateManyAndReturn<ExtArgs> | null
    /**
     * Omit specific fields from the Family
     */
    omit?: FamilyOmit<ExtArgs> | null
    /**
     * The data used to update Families.
     */
    data: XOR<FamilyUpdateManyMutationInput, FamilyUncheckedUpdateManyInput>
    /**
     * Filter which Families to update
     */
    where?: FamilyWhereInput
    /**
     * Limit how many Families to update.
     */
    limit?: number
  }

  /**
   * Family upsert
   */
  export type FamilyUpsertArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Family
     */
    select?: FamilySelect<ExtArgs> | null
    /**
     * Omit specific fields from the Family
     */
    omit?: FamilyOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: FamilyInclude<ExtArgs> | null
    /**
     * The filter to search for the Family to update in case it exists.
     */
    where: FamilyWhereUniqueInput
    /**
     * In case the Family found by the `where` argument doesn't exist, create a new Family with this data.
     */
    create: XOR<FamilyCreateInput, FamilyUncheckedCreateInput>
    /**
     * In case the Family was found with the provided `where` argument, update it with this data.
     */
    update: XOR<FamilyUpdateInput, FamilyUncheckedUpdateInput>
  }

  /**
   * Family delete
   */
  export type FamilyDeleteArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Family
     */
    select?: FamilySelect<ExtArgs> | null
    /**
     * Omit specific fields from the Family
     */
    omit?: FamilyOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: FamilyInclude<ExtArgs> | null
    /**
     * Filter which Family to delete.
     */
    where: FamilyWhereUniqueInput
  }

  /**
   * Family deleteMany
   */
  export type FamilyDeleteManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Filter which Families to delete
     */
    where?: FamilyWhereInput
    /**
     * Limit how many Families to delete.
     */
    limit?: number
  }

  /**
   * Family.parents
   */
  export type Family$parentsArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Parent
     */
    select?: ParentSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Parent
     */
    omit?: ParentOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: ParentInclude<ExtArgs> | null
    where?: ParentWhereInput
    orderBy?: ParentOrderByWithRelationInput | ParentOrderByWithRelationInput[]
    cursor?: ParentWhereUniqueInput
    take?: number
    skip?: number
    distinct?: ParentScalarFieldEnum | ParentScalarFieldEnum[]
  }

  /**
   * Family.children
   */
  export type Family$childrenArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Child
     */
    select?: ChildSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Child
     */
    omit?: ChildOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: ChildInclude<ExtArgs> | null
    where?: ChildWhereInput
    orderBy?: ChildOrderByWithRelationInput | ChildOrderByWithRelationInput[]
    cursor?: ChildWhereUniqueInput
    take?: number
    skip?: number
    distinct?: ChildScalarFieldEnum | ChildScalarFieldEnum[]
  }

  /**
   * Family without action
   */
  export type FamilyDefaultArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Family
     */
    select?: FamilySelect<ExtArgs> | null
    /**
     * Omit specific fields from the Family
     */
    omit?: FamilyOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: FamilyInclude<ExtArgs> | null
  }


  /**
   * Model Parent
   */

  export type AggregateParent = {
    _count: ParentCountAggregateOutputType | null
    _min: ParentMinAggregateOutputType | null
    _max: ParentMaxAggregateOutputType | null
  }

  export type ParentMinAggregateOutputType = {
    id: string | null
    name: string | null
    phone: string | null
    email: string | null
    relationshipType: string | null
    lastParticipationDate: Date | null
    familyId: string | null
  }

  export type ParentMaxAggregateOutputType = {
    id: string | null
    name: string | null
    phone: string | null
    email: string | null
    relationshipType: string | null
    lastParticipationDate: Date | null
    familyId: string | null
  }

  export type ParentCountAggregateOutputType = {
    id: number
    name: number
    phone: number
    email: number
    relationshipType: number
    lastParticipationDate: number
    familyId: number
    _all: number
  }


  export type ParentMinAggregateInputType = {
    id?: true
    name?: true
    phone?: true
    email?: true
    relationshipType?: true
    lastParticipationDate?: true
    familyId?: true
  }

  export type ParentMaxAggregateInputType = {
    id?: true
    name?: true
    phone?: true
    email?: true
    relationshipType?: true
    lastParticipationDate?: true
    familyId?: true
  }

  export type ParentCountAggregateInputType = {
    id?: true
    name?: true
    phone?: true
    email?: true
    relationshipType?: true
    lastParticipationDate?: true
    familyId?: true
    _all?: true
  }

  export type ParentAggregateArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Filter which Parent to aggregate.
     */
    where?: ParentWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of Parents to fetch.
     */
    orderBy?: ParentOrderByWithRelationInput | ParentOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the start position
     */
    cursor?: ParentWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` Parents from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` Parents.
     */
    skip?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/aggregations Aggregation Docs}
     * 
     * Count returned Parents
    **/
    _count?: true | ParentCountAggregateInputType
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/aggregations Aggregation Docs}
     * 
     * Select which fields to find the minimum value
    **/
    _min?: ParentMinAggregateInputType
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/aggregations Aggregation Docs}
     * 
     * Select which fields to find the maximum value
    **/
    _max?: ParentMaxAggregateInputType
  }

  export type GetParentAggregateType<T extends ParentAggregateArgs> = {
        [P in keyof T & keyof AggregateParent]: P extends '_count' | 'count'
      ? T[P] extends true
        ? number
        : GetScalarType<T[P], AggregateParent[P]>
      : GetScalarType<T[P], AggregateParent[P]>
  }




  export type ParentGroupByArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    where?: ParentWhereInput
    orderBy?: ParentOrderByWithAggregationInput | ParentOrderByWithAggregationInput[]
    by: ParentScalarFieldEnum[] | ParentScalarFieldEnum
    having?: ParentScalarWhereWithAggregatesInput
    take?: number
    skip?: number
    _count?: ParentCountAggregateInputType | true
    _min?: ParentMinAggregateInputType
    _max?: ParentMaxAggregateInputType
  }

  export type ParentGroupByOutputType = {
    id: string
    name: string
    phone: string | null
    email: string | null
    relationshipType: string
    lastParticipationDate: Date | null
    familyId: string
    _count: ParentCountAggregateOutputType | null
    _min: ParentMinAggregateOutputType | null
    _max: ParentMaxAggregateOutputType | null
  }

  type GetParentGroupByPayload<T extends ParentGroupByArgs> = Prisma.PrismaPromise<
    Array<
      PickEnumerable<ParentGroupByOutputType, T['by']> &
        {
          [P in ((keyof T) & (keyof ParentGroupByOutputType))]: P extends '_count'
            ? T[P] extends boolean
              ? number
              : GetScalarType<T[P], ParentGroupByOutputType[P]>
            : GetScalarType<T[P], ParentGroupByOutputType[P]>
        }
      >
    >


  export type ParentSelect<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetSelect<{
    id?: boolean
    name?: boolean
    phone?: boolean
    email?: boolean
    relationshipType?: boolean
    lastParticipationDate?: boolean
    familyId?: boolean
    family?: boolean | FamilyDefaultArgs<ExtArgs>
  }, ExtArgs["result"]["parent"]>

  export type ParentSelectCreateManyAndReturn<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetSelect<{
    id?: boolean
    name?: boolean
    phone?: boolean
    email?: boolean
    relationshipType?: boolean
    lastParticipationDate?: boolean
    familyId?: boolean
    family?: boolean | FamilyDefaultArgs<ExtArgs>
  }, ExtArgs["result"]["parent"]>

  export type ParentSelectUpdateManyAndReturn<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetSelect<{
    id?: boolean
    name?: boolean
    phone?: boolean
    email?: boolean
    relationshipType?: boolean
    lastParticipationDate?: boolean
    familyId?: boolean
    family?: boolean | FamilyDefaultArgs<ExtArgs>
  }, ExtArgs["result"]["parent"]>

  export type ParentSelectScalar = {
    id?: boolean
    name?: boolean
    phone?: boolean
    email?: boolean
    relationshipType?: boolean
    lastParticipationDate?: boolean
    familyId?: boolean
  }

  export type ParentOmit<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetOmit<"id" | "name" | "phone" | "email" | "relationshipType" | "lastParticipationDate" | "familyId", ExtArgs["result"]["parent"]>
  export type ParentInclude<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    family?: boolean | FamilyDefaultArgs<ExtArgs>
  }
  export type ParentIncludeCreateManyAndReturn<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    family?: boolean | FamilyDefaultArgs<ExtArgs>
  }
  export type ParentIncludeUpdateManyAndReturn<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    family?: boolean | FamilyDefaultArgs<ExtArgs>
  }

  export type $ParentPayload<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    name: "Parent"
    objects: {
      family: Prisma.$FamilyPayload<ExtArgs>
    }
    scalars: $Extensions.GetPayloadResult<{
      id: string
      name: string
      phone: string | null
      email: string | null
      relationshipType: string
      lastParticipationDate: Date | null
      familyId: string
    }, ExtArgs["result"]["parent"]>
    composites: {}
  }

  type ParentGetPayload<S extends boolean | null | undefined | ParentDefaultArgs> = $Result.GetResult<Prisma.$ParentPayload, S>

  type ParentCountArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> =
    Omit<ParentFindManyArgs, 'select' | 'include' | 'distinct' | 'omit'> & {
      select?: ParentCountAggregateInputType | true
    }

  export interface ParentDelegate<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs, GlobalOmitOptions = {}> {
    [K: symbol]: { types: Prisma.TypeMap<ExtArgs>['model']['Parent'], meta: { name: 'Parent' } }
    /**
     * Find zero or one Parent that matches the filter.
     * @param {ParentFindUniqueArgs} args - Arguments to find a Parent
     * @example
     * // Get one Parent
     * const parent = await prisma.parent.findUnique({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findUnique<T extends ParentFindUniqueArgs>(args: SelectSubset<T, ParentFindUniqueArgs<ExtArgs>>): Prisma__ParentClient<$Result.GetResult<Prisma.$ParentPayload<ExtArgs>, T, "findUnique", GlobalOmitOptions> | null, null, ExtArgs, GlobalOmitOptions>

    /**
     * Find one Parent that matches the filter or throw an error with `error.code='P2025'`
     * if no matches were found.
     * @param {ParentFindUniqueOrThrowArgs} args - Arguments to find a Parent
     * @example
     * // Get one Parent
     * const parent = await prisma.parent.findUniqueOrThrow({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findUniqueOrThrow<T extends ParentFindUniqueOrThrowArgs>(args: SelectSubset<T, ParentFindUniqueOrThrowArgs<ExtArgs>>): Prisma__ParentClient<$Result.GetResult<Prisma.$ParentPayload<ExtArgs>, T, "findUniqueOrThrow", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Find the first Parent that matches the filter.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {ParentFindFirstArgs} args - Arguments to find a Parent
     * @example
     * // Get one Parent
     * const parent = await prisma.parent.findFirst({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findFirst<T extends ParentFindFirstArgs>(args?: SelectSubset<T, ParentFindFirstArgs<ExtArgs>>): Prisma__ParentClient<$Result.GetResult<Prisma.$ParentPayload<ExtArgs>, T, "findFirst", GlobalOmitOptions> | null, null, ExtArgs, GlobalOmitOptions>

    /**
     * Find the first Parent that matches the filter or
     * throw `PrismaKnownClientError` with `P2025` code if no matches were found.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {ParentFindFirstOrThrowArgs} args - Arguments to find a Parent
     * @example
     * // Get one Parent
     * const parent = await prisma.parent.findFirstOrThrow({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findFirstOrThrow<T extends ParentFindFirstOrThrowArgs>(args?: SelectSubset<T, ParentFindFirstOrThrowArgs<ExtArgs>>): Prisma__ParentClient<$Result.GetResult<Prisma.$ParentPayload<ExtArgs>, T, "findFirstOrThrow", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Find zero or more Parents that matches the filter.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {ParentFindManyArgs} args - Arguments to filter and select certain fields only.
     * @example
     * // Get all Parents
     * const parents = await prisma.parent.findMany()
     * 
     * // Get first 10 Parents
     * const parents = await prisma.parent.findMany({ take: 10 })
     * 
     * // Only select the `id`
     * const parentWithIdOnly = await prisma.parent.findMany({ select: { id: true } })
     * 
     */
    findMany<T extends ParentFindManyArgs>(args?: SelectSubset<T, ParentFindManyArgs<ExtArgs>>): Prisma.PrismaPromise<$Result.GetResult<Prisma.$ParentPayload<ExtArgs>, T, "findMany", GlobalOmitOptions>>

    /**
     * Create a Parent.
     * @param {ParentCreateArgs} args - Arguments to create a Parent.
     * @example
     * // Create one Parent
     * const Parent = await prisma.parent.create({
     *   data: {
     *     // ... data to create a Parent
     *   }
     * })
     * 
     */
    create<T extends ParentCreateArgs>(args: SelectSubset<T, ParentCreateArgs<ExtArgs>>): Prisma__ParentClient<$Result.GetResult<Prisma.$ParentPayload<ExtArgs>, T, "create", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Create many Parents.
     * @param {ParentCreateManyArgs} args - Arguments to create many Parents.
     * @example
     * // Create many Parents
     * const parent = await prisma.parent.createMany({
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     *     
     */
    createMany<T extends ParentCreateManyArgs>(args?: SelectSubset<T, ParentCreateManyArgs<ExtArgs>>): Prisma.PrismaPromise<BatchPayload>

    /**
     * Create many Parents and returns the data saved in the database.
     * @param {ParentCreateManyAndReturnArgs} args - Arguments to create many Parents.
     * @example
     * // Create many Parents
     * const parent = await prisma.parent.createManyAndReturn({
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * 
     * // Create many Parents and only return the `id`
     * const parentWithIdOnly = await prisma.parent.createManyAndReturn({
     *   select: { id: true },
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * 
     */
    createManyAndReturn<T extends ParentCreateManyAndReturnArgs>(args?: SelectSubset<T, ParentCreateManyAndReturnArgs<ExtArgs>>): Prisma.PrismaPromise<$Result.GetResult<Prisma.$ParentPayload<ExtArgs>, T, "createManyAndReturn", GlobalOmitOptions>>

    /**
     * Delete a Parent.
     * @param {ParentDeleteArgs} args - Arguments to delete one Parent.
     * @example
     * // Delete one Parent
     * const Parent = await prisma.parent.delete({
     *   where: {
     *     // ... filter to delete one Parent
     *   }
     * })
     * 
     */
    delete<T extends ParentDeleteArgs>(args: SelectSubset<T, ParentDeleteArgs<ExtArgs>>): Prisma__ParentClient<$Result.GetResult<Prisma.$ParentPayload<ExtArgs>, T, "delete", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Update one Parent.
     * @param {ParentUpdateArgs} args - Arguments to update one Parent.
     * @example
     * // Update one Parent
     * const parent = await prisma.parent.update({
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: {
     *     // ... provide data here
     *   }
     * })
     * 
     */
    update<T extends ParentUpdateArgs>(args: SelectSubset<T, ParentUpdateArgs<ExtArgs>>): Prisma__ParentClient<$Result.GetResult<Prisma.$ParentPayload<ExtArgs>, T, "update", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Delete zero or more Parents.
     * @param {ParentDeleteManyArgs} args - Arguments to filter Parents to delete.
     * @example
     * // Delete a few Parents
     * const { count } = await prisma.parent.deleteMany({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     * 
     */
    deleteMany<T extends ParentDeleteManyArgs>(args?: SelectSubset<T, ParentDeleteManyArgs<ExtArgs>>): Prisma.PrismaPromise<BatchPayload>

    /**
     * Update zero or more Parents.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {ParentUpdateManyArgs} args - Arguments to update one or more rows.
     * @example
     * // Update many Parents
     * const parent = await prisma.parent.updateMany({
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: {
     *     // ... provide data here
     *   }
     * })
     * 
     */
    updateMany<T extends ParentUpdateManyArgs>(args: SelectSubset<T, ParentUpdateManyArgs<ExtArgs>>): Prisma.PrismaPromise<BatchPayload>

    /**
     * Update zero or more Parents and returns the data updated in the database.
     * @param {ParentUpdateManyAndReturnArgs} args - Arguments to update many Parents.
     * @example
     * // Update many Parents
     * const parent = await prisma.parent.updateManyAndReturn({
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * 
     * // Update zero or more Parents and only return the `id`
     * const parentWithIdOnly = await prisma.parent.updateManyAndReturn({
     *   select: { id: true },
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * 
     */
    updateManyAndReturn<T extends ParentUpdateManyAndReturnArgs>(args: SelectSubset<T, ParentUpdateManyAndReturnArgs<ExtArgs>>): Prisma.PrismaPromise<$Result.GetResult<Prisma.$ParentPayload<ExtArgs>, T, "updateManyAndReturn", GlobalOmitOptions>>

    /**
     * Create or update one Parent.
     * @param {ParentUpsertArgs} args - Arguments to update or create a Parent.
     * @example
     * // Update or create a Parent
     * const parent = await prisma.parent.upsert({
     *   create: {
     *     // ... data to create a Parent
     *   },
     *   update: {
     *     // ... in case it already exists, update
     *   },
     *   where: {
     *     // ... the filter for the Parent we want to update
     *   }
     * })
     */
    upsert<T extends ParentUpsertArgs>(args: SelectSubset<T, ParentUpsertArgs<ExtArgs>>): Prisma__ParentClient<$Result.GetResult<Prisma.$ParentPayload<ExtArgs>, T, "upsert", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>


    /**
     * Count the number of Parents.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {ParentCountArgs} args - Arguments to filter Parents to count.
     * @example
     * // Count the number of Parents
     * const count = await prisma.parent.count({
     *   where: {
     *     // ... the filter for the Parents we want to count
     *   }
     * })
    **/
    count<T extends ParentCountArgs>(
      args?: Subset<T, ParentCountArgs>,
    ): Prisma.PrismaPromise<
      T extends $Utils.Record<'select', any>
        ? T['select'] extends true
          ? number
          : GetScalarType<T['select'], ParentCountAggregateOutputType>
        : number
    >

    /**
     * Allows you to perform aggregations operations on a Parent.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {ParentAggregateArgs} args - Select which aggregations you would like to apply and on what fields.
     * @example
     * // Ordered by age ascending
     * // Where email contains prisma.io
     * // Limited to the 10 users
     * const aggregations = await prisma.user.aggregate({
     *   _avg: {
     *     age: true,
     *   },
     *   where: {
     *     email: {
     *       contains: "prisma.io",
     *     },
     *   },
     *   orderBy: {
     *     age: "asc",
     *   },
     *   take: 10,
     * })
    **/
    aggregate<T extends ParentAggregateArgs>(args: Subset<T, ParentAggregateArgs>): Prisma.PrismaPromise<GetParentAggregateType<T>>

    /**
     * Group by Parent.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {ParentGroupByArgs} args - Group by arguments.
     * @example
     * // Group by city, order by createdAt, get count
     * const result = await prisma.user.groupBy({
     *   by: ['city', 'createdAt'],
     *   orderBy: {
     *     createdAt: true
     *   },
     *   _count: {
     *     _all: true
     *   },
     * })
     * 
    **/
    groupBy<
      T extends ParentGroupByArgs,
      HasSelectOrTake extends Or<
        Extends<'skip', Keys<T>>,
        Extends<'take', Keys<T>>
      >,
      OrderByArg extends True extends HasSelectOrTake
        ? { orderBy: ParentGroupByArgs['orderBy'] }
        : { orderBy?: ParentGroupByArgs['orderBy'] },
      OrderFields extends ExcludeUnderscoreKeys<Keys<MaybeTupleToUnion<T['orderBy']>>>,
      ByFields extends MaybeTupleToUnion<T['by']>,
      ByValid extends Has<ByFields, OrderFields>,
      HavingFields extends GetHavingFields<T['having']>,
      HavingValid extends Has<ByFields, HavingFields>,
      ByEmpty extends T['by'] extends never[] ? True : False,
      InputErrors extends ByEmpty extends True
      ? `Error: "by" must not be empty.`
      : HavingValid extends False
      ? {
          [P in HavingFields]: P extends ByFields
            ? never
            : P extends string
            ? `Error: Field "${P}" used in "having" needs to be provided in "by".`
            : [
                Error,
                'Field ',
                P,
                ` in "having" needs to be provided in "by"`,
              ]
        }[HavingFields]
      : 'take' extends Keys<T>
      ? 'orderBy' extends Keys<T>
        ? ByValid extends True
          ? {}
          : {
              [P in OrderFields]: P extends ByFields
                ? never
                : `Error: Field "${P}" in "orderBy" needs to be provided in "by"`
            }[OrderFields]
        : 'Error: If you provide "take", you also need to provide "orderBy"'
      : 'skip' extends Keys<T>
      ? 'orderBy' extends Keys<T>
        ? ByValid extends True
          ? {}
          : {
              [P in OrderFields]: P extends ByFields
                ? never
                : `Error: Field "${P}" in "orderBy" needs to be provided in "by"`
            }[OrderFields]
        : 'Error: If you provide "skip", you also need to provide "orderBy"'
      : ByValid extends True
      ? {}
      : {
          [P in OrderFields]: P extends ByFields
            ? never
            : `Error: Field "${P}" in "orderBy" needs to be provided in "by"`
        }[OrderFields]
    >(args: SubsetIntersection<T, ParentGroupByArgs, OrderByArg> & InputErrors): {} extends InputErrors ? GetParentGroupByPayload<T> : Prisma.PrismaPromise<InputErrors>
  /**
   * Fields of the Parent model
   */
  readonly fields: ParentFieldRefs;
  }

  /**
   * The delegate class that acts as a "Promise-like" for Parent.
   * Why is this prefixed with `Prisma__`?
   * Because we want to prevent naming conflicts as mentioned in
   * https://github.com/prisma/prisma-client-js/issues/707
   */
  export interface Prisma__ParentClient<T, Null = never, ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs, GlobalOmitOptions = {}> extends Prisma.PrismaPromise<T> {
    readonly [Symbol.toStringTag]: "PrismaPromise"
    family<T extends FamilyDefaultArgs<ExtArgs> = {}>(args?: Subset<T, FamilyDefaultArgs<ExtArgs>>): Prisma__FamilyClient<$Result.GetResult<Prisma.$FamilyPayload<ExtArgs>, T, "findUniqueOrThrow", GlobalOmitOptions> | Null, Null, ExtArgs, GlobalOmitOptions>
    /**
     * Attaches callbacks for the resolution and/or rejection of the Promise.
     * @param onfulfilled The callback to execute when the Promise is resolved.
     * @param onrejected The callback to execute when the Promise is rejected.
     * @returns A Promise for the completion of which ever callback is executed.
     */
    then<TResult1 = T, TResult2 = never>(onfulfilled?: ((value: T) => TResult1 | PromiseLike<TResult1>) | undefined | null, onrejected?: ((reason: any) => TResult2 | PromiseLike<TResult2>) | undefined | null): $Utils.JsPromise<TResult1 | TResult2>
    /**
     * Attaches a callback for only the rejection of the Promise.
     * @param onrejected The callback to execute when the Promise is rejected.
     * @returns A Promise for the completion of the callback.
     */
    catch<TResult = never>(onrejected?: ((reason: any) => TResult | PromiseLike<TResult>) | undefined | null): $Utils.JsPromise<T | TResult>
    /**
     * Attaches a callback that is invoked when the Promise is settled (fulfilled or rejected). The
     * resolved value cannot be modified from the callback.
     * @param onfinally The callback to execute when the Promise is settled (fulfilled or rejected).
     * @returns A Promise for the completion of the callback.
     */
    finally(onfinally?: (() => void) | undefined | null): $Utils.JsPromise<T>
  }




  /**
   * Fields of the Parent model
   */
  interface ParentFieldRefs {
    readonly id: FieldRef<"Parent", 'String'>
    readonly name: FieldRef<"Parent", 'String'>
    readonly phone: FieldRef<"Parent", 'String'>
    readonly email: FieldRef<"Parent", 'String'>
    readonly relationshipType: FieldRef<"Parent", 'String'>
    readonly lastParticipationDate: FieldRef<"Parent", 'DateTime'>
    readonly familyId: FieldRef<"Parent", 'String'>
  }
    

  // Custom InputTypes
  /**
   * Parent findUnique
   */
  export type ParentFindUniqueArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Parent
     */
    select?: ParentSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Parent
     */
    omit?: ParentOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: ParentInclude<ExtArgs> | null
    /**
     * Filter, which Parent to fetch.
     */
    where: ParentWhereUniqueInput
  }

  /**
   * Parent findUniqueOrThrow
   */
  export type ParentFindUniqueOrThrowArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Parent
     */
    select?: ParentSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Parent
     */
    omit?: ParentOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: ParentInclude<ExtArgs> | null
    /**
     * Filter, which Parent to fetch.
     */
    where: ParentWhereUniqueInput
  }

  /**
   * Parent findFirst
   */
  export type ParentFindFirstArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Parent
     */
    select?: ParentSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Parent
     */
    omit?: ParentOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: ParentInclude<ExtArgs> | null
    /**
     * Filter, which Parent to fetch.
     */
    where?: ParentWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of Parents to fetch.
     */
    orderBy?: ParentOrderByWithRelationInput | ParentOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the position for searching for Parents.
     */
    cursor?: ParentWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` Parents from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` Parents.
     */
    skip?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/distinct Distinct Docs}
     * 
     * Filter by unique combinations of Parents.
     */
    distinct?: ParentScalarFieldEnum | ParentScalarFieldEnum[]
  }

  /**
   * Parent findFirstOrThrow
   */
  export type ParentFindFirstOrThrowArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Parent
     */
    select?: ParentSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Parent
     */
    omit?: ParentOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: ParentInclude<ExtArgs> | null
    /**
     * Filter, which Parent to fetch.
     */
    where?: ParentWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of Parents to fetch.
     */
    orderBy?: ParentOrderByWithRelationInput | ParentOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the position for searching for Parents.
     */
    cursor?: ParentWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` Parents from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` Parents.
     */
    skip?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/distinct Distinct Docs}
     * 
     * Filter by unique combinations of Parents.
     */
    distinct?: ParentScalarFieldEnum | ParentScalarFieldEnum[]
  }

  /**
   * Parent findMany
   */
  export type ParentFindManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Parent
     */
    select?: ParentSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Parent
     */
    omit?: ParentOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: ParentInclude<ExtArgs> | null
    /**
     * Filter, which Parents to fetch.
     */
    where?: ParentWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of Parents to fetch.
     */
    orderBy?: ParentOrderByWithRelationInput | ParentOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the position for listing Parents.
     */
    cursor?: ParentWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` Parents from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` Parents.
     */
    skip?: number
    distinct?: ParentScalarFieldEnum | ParentScalarFieldEnum[]
  }

  /**
   * Parent create
   */
  export type ParentCreateArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Parent
     */
    select?: ParentSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Parent
     */
    omit?: ParentOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: ParentInclude<ExtArgs> | null
    /**
     * The data needed to create a Parent.
     */
    data: XOR<ParentCreateInput, ParentUncheckedCreateInput>
  }

  /**
   * Parent createMany
   */
  export type ParentCreateManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * The data used to create many Parents.
     */
    data: ParentCreateManyInput | ParentCreateManyInput[]
    skipDuplicates?: boolean
  }

  /**
   * Parent createManyAndReturn
   */
  export type ParentCreateManyAndReturnArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Parent
     */
    select?: ParentSelectCreateManyAndReturn<ExtArgs> | null
    /**
     * Omit specific fields from the Parent
     */
    omit?: ParentOmit<ExtArgs> | null
    /**
     * The data used to create many Parents.
     */
    data: ParentCreateManyInput | ParentCreateManyInput[]
    skipDuplicates?: boolean
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: ParentIncludeCreateManyAndReturn<ExtArgs> | null
  }

  /**
   * Parent update
   */
  export type ParentUpdateArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Parent
     */
    select?: ParentSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Parent
     */
    omit?: ParentOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: ParentInclude<ExtArgs> | null
    /**
     * The data needed to update a Parent.
     */
    data: XOR<ParentUpdateInput, ParentUncheckedUpdateInput>
    /**
     * Choose, which Parent to update.
     */
    where: ParentWhereUniqueInput
  }

  /**
   * Parent updateMany
   */
  export type ParentUpdateManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * The data used to update Parents.
     */
    data: XOR<ParentUpdateManyMutationInput, ParentUncheckedUpdateManyInput>
    /**
     * Filter which Parents to update
     */
    where?: ParentWhereInput
    /**
     * Limit how many Parents to update.
     */
    limit?: number
  }

  /**
   * Parent updateManyAndReturn
   */
  export type ParentUpdateManyAndReturnArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Parent
     */
    select?: ParentSelectUpdateManyAndReturn<ExtArgs> | null
    /**
     * Omit specific fields from the Parent
     */
    omit?: ParentOmit<ExtArgs> | null
    /**
     * The data used to update Parents.
     */
    data: XOR<ParentUpdateManyMutationInput, ParentUncheckedUpdateManyInput>
    /**
     * Filter which Parents to update
     */
    where?: ParentWhereInput
    /**
     * Limit how many Parents to update.
     */
    limit?: number
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: ParentIncludeUpdateManyAndReturn<ExtArgs> | null
  }

  /**
   * Parent upsert
   */
  export type ParentUpsertArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Parent
     */
    select?: ParentSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Parent
     */
    omit?: ParentOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: ParentInclude<ExtArgs> | null
    /**
     * The filter to search for the Parent to update in case it exists.
     */
    where: ParentWhereUniqueInput
    /**
     * In case the Parent found by the `where` argument doesn't exist, create a new Parent with this data.
     */
    create: XOR<ParentCreateInput, ParentUncheckedCreateInput>
    /**
     * In case the Parent was found with the provided `where` argument, update it with this data.
     */
    update: XOR<ParentUpdateInput, ParentUncheckedUpdateInput>
  }

  /**
   * Parent delete
   */
  export type ParentDeleteArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Parent
     */
    select?: ParentSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Parent
     */
    omit?: ParentOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: ParentInclude<ExtArgs> | null
    /**
     * Filter which Parent to delete.
     */
    where: ParentWhereUniqueInput
  }

  /**
   * Parent deleteMany
   */
  export type ParentDeleteManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Filter which Parents to delete
     */
    where?: ParentWhereInput
    /**
     * Limit how many Parents to delete.
     */
    limit?: number
  }

  /**
   * Parent without action
   */
  export type ParentDefaultArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Parent
     */
    select?: ParentSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Parent
     */
    omit?: ParentOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: ParentInclude<ExtArgs> | null
  }


  /**
   * Model Child
   */

  export type AggregateChild = {
    _count: ChildCountAggregateOutputType | null
    _min: ChildMinAggregateOutputType | null
    _max: ChildMaxAggregateOutputType | null
  }

  export type ChildMinAggregateOutputType = {
    id: string | null
    firstName: string | null
    lastName: string | null
    birthdate: Date | null
    allergies: string | null
    notes: string | null
    qrToken: string | null
    lastParticipationDate: Date | null
    familyId: string | null
  }

  export type ChildMaxAggregateOutputType = {
    id: string | null
    firstName: string | null
    lastName: string | null
    birthdate: Date | null
    allergies: string | null
    notes: string | null
    qrToken: string | null
    lastParticipationDate: Date | null
    familyId: string | null
  }

  export type ChildCountAggregateOutputType = {
    id: number
    firstName: number
    lastName: number
    birthdate: number
    allergies: number
    notes: number
    qrToken: number
    lastParticipationDate: number
    familyId: number
    _all: number
  }


  export type ChildMinAggregateInputType = {
    id?: true
    firstName?: true
    lastName?: true
    birthdate?: true
    allergies?: true
    notes?: true
    qrToken?: true
    lastParticipationDate?: true
    familyId?: true
  }

  export type ChildMaxAggregateInputType = {
    id?: true
    firstName?: true
    lastName?: true
    birthdate?: true
    allergies?: true
    notes?: true
    qrToken?: true
    lastParticipationDate?: true
    familyId?: true
  }

  export type ChildCountAggregateInputType = {
    id?: true
    firstName?: true
    lastName?: true
    birthdate?: true
    allergies?: true
    notes?: true
    qrToken?: true
    lastParticipationDate?: true
    familyId?: true
    _all?: true
  }

  export type ChildAggregateArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Filter which Child to aggregate.
     */
    where?: ChildWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of Children to fetch.
     */
    orderBy?: ChildOrderByWithRelationInput | ChildOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the start position
     */
    cursor?: ChildWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` Children from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` Children.
     */
    skip?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/aggregations Aggregation Docs}
     * 
     * Count returned Children
    **/
    _count?: true | ChildCountAggregateInputType
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/aggregations Aggregation Docs}
     * 
     * Select which fields to find the minimum value
    **/
    _min?: ChildMinAggregateInputType
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/aggregations Aggregation Docs}
     * 
     * Select which fields to find the maximum value
    **/
    _max?: ChildMaxAggregateInputType
  }

  export type GetChildAggregateType<T extends ChildAggregateArgs> = {
        [P in keyof T & keyof AggregateChild]: P extends '_count' | 'count'
      ? T[P] extends true
        ? number
        : GetScalarType<T[P], AggregateChild[P]>
      : GetScalarType<T[P], AggregateChild[P]>
  }




  export type ChildGroupByArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    where?: ChildWhereInput
    orderBy?: ChildOrderByWithAggregationInput | ChildOrderByWithAggregationInput[]
    by: ChildScalarFieldEnum[] | ChildScalarFieldEnum
    having?: ChildScalarWhereWithAggregatesInput
    take?: number
    skip?: number
    _count?: ChildCountAggregateInputType | true
    _min?: ChildMinAggregateInputType
    _max?: ChildMaxAggregateInputType
  }

  export type ChildGroupByOutputType = {
    id: string
    firstName: string
    lastName: string
    birthdate: Date
    allergies: string | null
    notes: string | null
    qrToken: string | null
    lastParticipationDate: Date | null
    familyId: string
    _count: ChildCountAggregateOutputType | null
    _min: ChildMinAggregateOutputType | null
    _max: ChildMaxAggregateOutputType | null
  }

  type GetChildGroupByPayload<T extends ChildGroupByArgs> = Prisma.PrismaPromise<
    Array<
      PickEnumerable<ChildGroupByOutputType, T['by']> &
        {
          [P in ((keyof T) & (keyof ChildGroupByOutputType))]: P extends '_count'
            ? T[P] extends boolean
              ? number
              : GetScalarType<T[P], ChildGroupByOutputType[P]>
            : GetScalarType<T[P], ChildGroupByOutputType[P]>
        }
      >
    >


  export type ChildSelect<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetSelect<{
    id?: boolean
    firstName?: boolean
    lastName?: boolean
    birthdate?: boolean
    allergies?: boolean
    notes?: boolean
    qrToken?: boolean
    lastParticipationDate?: boolean
    familyId?: boolean
    family?: boolean | FamilyDefaultArgs<ExtArgs>
    checkInRecords?: boolean | Child$checkInRecordsArgs<ExtArgs>
    tickets?: boolean | Child$ticketsArgs<ExtArgs>
    _count?: boolean | ChildCountOutputTypeDefaultArgs<ExtArgs>
  }, ExtArgs["result"]["child"]>

  export type ChildSelectCreateManyAndReturn<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetSelect<{
    id?: boolean
    firstName?: boolean
    lastName?: boolean
    birthdate?: boolean
    allergies?: boolean
    notes?: boolean
    qrToken?: boolean
    lastParticipationDate?: boolean
    familyId?: boolean
    family?: boolean | FamilyDefaultArgs<ExtArgs>
  }, ExtArgs["result"]["child"]>

  export type ChildSelectUpdateManyAndReturn<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetSelect<{
    id?: boolean
    firstName?: boolean
    lastName?: boolean
    birthdate?: boolean
    allergies?: boolean
    notes?: boolean
    qrToken?: boolean
    lastParticipationDate?: boolean
    familyId?: boolean
    family?: boolean | FamilyDefaultArgs<ExtArgs>
  }, ExtArgs["result"]["child"]>

  export type ChildSelectScalar = {
    id?: boolean
    firstName?: boolean
    lastName?: boolean
    birthdate?: boolean
    allergies?: boolean
    notes?: boolean
    qrToken?: boolean
    lastParticipationDate?: boolean
    familyId?: boolean
  }

  export type ChildOmit<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetOmit<"id" | "firstName" | "lastName" | "birthdate" | "allergies" | "notes" | "qrToken" | "lastParticipationDate" | "familyId", ExtArgs["result"]["child"]>
  export type ChildInclude<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    family?: boolean | FamilyDefaultArgs<ExtArgs>
    checkInRecords?: boolean | Child$checkInRecordsArgs<ExtArgs>
    tickets?: boolean | Child$ticketsArgs<ExtArgs>
    _count?: boolean | ChildCountOutputTypeDefaultArgs<ExtArgs>
  }
  export type ChildIncludeCreateManyAndReturn<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    family?: boolean | FamilyDefaultArgs<ExtArgs>
  }
  export type ChildIncludeUpdateManyAndReturn<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    family?: boolean | FamilyDefaultArgs<ExtArgs>
  }

  export type $ChildPayload<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    name: "Child"
    objects: {
      family: Prisma.$FamilyPayload<ExtArgs>
      checkInRecords: Prisma.$CheckInRecordPayload<ExtArgs>[]
      tickets: Prisma.$TicketPayload<ExtArgs>[]
    }
    scalars: $Extensions.GetPayloadResult<{
      id: string
      firstName: string
      lastName: string
      birthdate: Date
      allergies: string | null
      notes: string | null
      qrToken: string | null
      lastParticipationDate: Date | null
      familyId: string
    }, ExtArgs["result"]["child"]>
    composites: {}
  }

  type ChildGetPayload<S extends boolean | null | undefined | ChildDefaultArgs> = $Result.GetResult<Prisma.$ChildPayload, S>

  type ChildCountArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> =
    Omit<ChildFindManyArgs, 'select' | 'include' | 'distinct' | 'omit'> & {
      select?: ChildCountAggregateInputType | true
    }

  export interface ChildDelegate<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs, GlobalOmitOptions = {}> {
    [K: symbol]: { types: Prisma.TypeMap<ExtArgs>['model']['Child'], meta: { name: 'Child' } }
    /**
     * Find zero or one Child that matches the filter.
     * @param {ChildFindUniqueArgs} args - Arguments to find a Child
     * @example
     * // Get one Child
     * const child = await prisma.child.findUnique({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findUnique<T extends ChildFindUniqueArgs>(args: SelectSubset<T, ChildFindUniqueArgs<ExtArgs>>): Prisma__ChildClient<$Result.GetResult<Prisma.$ChildPayload<ExtArgs>, T, "findUnique", GlobalOmitOptions> | null, null, ExtArgs, GlobalOmitOptions>

    /**
     * Find one Child that matches the filter or throw an error with `error.code='P2025'`
     * if no matches were found.
     * @param {ChildFindUniqueOrThrowArgs} args - Arguments to find a Child
     * @example
     * // Get one Child
     * const child = await prisma.child.findUniqueOrThrow({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findUniqueOrThrow<T extends ChildFindUniqueOrThrowArgs>(args: SelectSubset<T, ChildFindUniqueOrThrowArgs<ExtArgs>>): Prisma__ChildClient<$Result.GetResult<Prisma.$ChildPayload<ExtArgs>, T, "findUniqueOrThrow", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Find the first Child that matches the filter.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {ChildFindFirstArgs} args - Arguments to find a Child
     * @example
     * // Get one Child
     * const child = await prisma.child.findFirst({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findFirst<T extends ChildFindFirstArgs>(args?: SelectSubset<T, ChildFindFirstArgs<ExtArgs>>): Prisma__ChildClient<$Result.GetResult<Prisma.$ChildPayload<ExtArgs>, T, "findFirst", GlobalOmitOptions> | null, null, ExtArgs, GlobalOmitOptions>

    /**
     * Find the first Child that matches the filter or
     * throw `PrismaKnownClientError` with `P2025` code if no matches were found.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {ChildFindFirstOrThrowArgs} args - Arguments to find a Child
     * @example
     * // Get one Child
     * const child = await prisma.child.findFirstOrThrow({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findFirstOrThrow<T extends ChildFindFirstOrThrowArgs>(args?: SelectSubset<T, ChildFindFirstOrThrowArgs<ExtArgs>>): Prisma__ChildClient<$Result.GetResult<Prisma.$ChildPayload<ExtArgs>, T, "findFirstOrThrow", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Find zero or more Children that matches the filter.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {ChildFindManyArgs} args - Arguments to filter and select certain fields only.
     * @example
     * // Get all Children
     * const children = await prisma.child.findMany()
     * 
     * // Get first 10 Children
     * const children = await prisma.child.findMany({ take: 10 })
     * 
     * // Only select the `id`
     * const childWithIdOnly = await prisma.child.findMany({ select: { id: true } })
     * 
     */
    findMany<T extends ChildFindManyArgs>(args?: SelectSubset<T, ChildFindManyArgs<ExtArgs>>): Prisma.PrismaPromise<$Result.GetResult<Prisma.$ChildPayload<ExtArgs>, T, "findMany", GlobalOmitOptions>>

    /**
     * Create a Child.
     * @param {ChildCreateArgs} args - Arguments to create a Child.
     * @example
     * // Create one Child
     * const Child = await prisma.child.create({
     *   data: {
     *     // ... data to create a Child
     *   }
     * })
     * 
     */
    create<T extends ChildCreateArgs>(args: SelectSubset<T, ChildCreateArgs<ExtArgs>>): Prisma__ChildClient<$Result.GetResult<Prisma.$ChildPayload<ExtArgs>, T, "create", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Create many Children.
     * @param {ChildCreateManyArgs} args - Arguments to create many Children.
     * @example
     * // Create many Children
     * const child = await prisma.child.createMany({
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     *     
     */
    createMany<T extends ChildCreateManyArgs>(args?: SelectSubset<T, ChildCreateManyArgs<ExtArgs>>): Prisma.PrismaPromise<BatchPayload>

    /**
     * Create many Children and returns the data saved in the database.
     * @param {ChildCreateManyAndReturnArgs} args - Arguments to create many Children.
     * @example
     * // Create many Children
     * const child = await prisma.child.createManyAndReturn({
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * 
     * // Create many Children and only return the `id`
     * const childWithIdOnly = await prisma.child.createManyAndReturn({
     *   select: { id: true },
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * 
     */
    createManyAndReturn<T extends ChildCreateManyAndReturnArgs>(args?: SelectSubset<T, ChildCreateManyAndReturnArgs<ExtArgs>>): Prisma.PrismaPromise<$Result.GetResult<Prisma.$ChildPayload<ExtArgs>, T, "createManyAndReturn", GlobalOmitOptions>>

    /**
     * Delete a Child.
     * @param {ChildDeleteArgs} args - Arguments to delete one Child.
     * @example
     * // Delete one Child
     * const Child = await prisma.child.delete({
     *   where: {
     *     // ... filter to delete one Child
     *   }
     * })
     * 
     */
    delete<T extends ChildDeleteArgs>(args: SelectSubset<T, ChildDeleteArgs<ExtArgs>>): Prisma__ChildClient<$Result.GetResult<Prisma.$ChildPayload<ExtArgs>, T, "delete", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Update one Child.
     * @param {ChildUpdateArgs} args - Arguments to update one Child.
     * @example
     * // Update one Child
     * const child = await prisma.child.update({
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: {
     *     // ... provide data here
     *   }
     * })
     * 
     */
    update<T extends ChildUpdateArgs>(args: SelectSubset<T, ChildUpdateArgs<ExtArgs>>): Prisma__ChildClient<$Result.GetResult<Prisma.$ChildPayload<ExtArgs>, T, "update", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Delete zero or more Children.
     * @param {ChildDeleteManyArgs} args - Arguments to filter Children to delete.
     * @example
     * // Delete a few Children
     * const { count } = await prisma.child.deleteMany({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     * 
     */
    deleteMany<T extends ChildDeleteManyArgs>(args?: SelectSubset<T, ChildDeleteManyArgs<ExtArgs>>): Prisma.PrismaPromise<BatchPayload>

    /**
     * Update zero or more Children.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {ChildUpdateManyArgs} args - Arguments to update one or more rows.
     * @example
     * // Update many Children
     * const child = await prisma.child.updateMany({
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: {
     *     // ... provide data here
     *   }
     * })
     * 
     */
    updateMany<T extends ChildUpdateManyArgs>(args: SelectSubset<T, ChildUpdateManyArgs<ExtArgs>>): Prisma.PrismaPromise<BatchPayload>

    /**
     * Update zero or more Children and returns the data updated in the database.
     * @param {ChildUpdateManyAndReturnArgs} args - Arguments to update many Children.
     * @example
     * // Update many Children
     * const child = await prisma.child.updateManyAndReturn({
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * 
     * // Update zero or more Children and only return the `id`
     * const childWithIdOnly = await prisma.child.updateManyAndReturn({
     *   select: { id: true },
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * 
     */
    updateManyAndReturn<T extends ChildUpdateManyAndReturnArgs>(args: SelectSubset<T, ChildUpdateManyAndReturnArgs<ExtArgs>>): Prisma.PrismaPromise<$Result.GetResult<Prisma.$ChildPayload<ExtArgs>, T, "updateManyAndReturn", GlobalOmitOptions>>

    /**
     * Create or update one Child.
     * @param {ChildUpsertArgs} args - Arguments to update or create a Child.
     * @example
     * // Update or create a Child
     * const child = await prisma.child.upsert({
     *   create: {
     *     // ... data to create a Child
     *   },
     *   update: {
     *     // ... in case it already exists, update
     *   },
     *   where: {
     *     // ... the filter for the Child we want to update
     *   }
     * })
     */
    upsert<T extends ChildUpsertArgs>(args: SelectSubset<T, ChildUpsertArgs<ExtArgs>>): Prisma__ChildClient<$Result.GetResult<Prisma.$ChildPayload<ExtArgs>, T, "upsert", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>


    /**
     * Count the number of Children.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {ChildCountArgs} args - Arguments to filter Children to count.
     * @example
     * // Count the number of Children
     * const count = await prisma.child.count({
     *   where: {
     *     // ... the filter for the Children we want to count
     *   }
     * })
    **/
    count<T extends ChildCountArgs>(
      args?: Subset<T, ChildCountArgs>,
    ): Prisma.PrismaPromise<
      T extends $Utils.Record<'select', any>
        ? T['select'] extends true
          ? number
          : GetScalarType<T['select'], ChildCountAggregateOutputType>
        : number
    >

    /**
     * Allows you to perform aggregations operations on a Child.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {ChildAggregateArgs} args - Select which aggregations you would like to apply and on what fields.
     * @example
     * // Ordered by age ascending
     * // Where email contains prisma.io
     * // Limited to the 10 users
     * const aggregations = await prisma.user.aggregate({
     *   _avg: {
     *     age: true,
     *   },
     *   where: {
     *     email: {
     *       contains: "prisma.io",
     *     },
     *   },
     *   orderBy: {
     *     age: "asc",
     *   },
     *   take: 10,
     * })
    **/
    aggregate<T extends ChildAggregateArgs>(args: Subset<T, ChildAggregateArgs>): Prisma.PrismaPromise<GetChildAggregateType<T>>

    /**
     * Group by Child.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {ChildGroupByArgs} args - Group by arguments.
     * @example
     * // Group by city, order by createdAt, get count
     * const result = await prisma.user.groupBy({
     *   by: ['city', 'createdAt'],
     *   orderBy: {
     *     createdAt: true
     *   },
     *   _count: {
     *     _all: true
     *   },
     * })
     * 
    **/
    groupBy<
      T extends ChildGroupByArgs,
      HasSelectOrTake extends Or<
        Extends<'skip', Keys<T>>,
        Extends<'take', Keys<T>>
      >,
      OrderByArg extends True extends HasSelectOrTake
        ? { orderBy: ChildGroupByArgs['orderBy'] }
        : { orderBy?: ChildGroupByArgs['orderBy'] },
      OrderFields extends ExcludeUnderscoreKeys<Keys<MaybeTupleToUnion<T['orderBy']>>>,
      ByFields extends MaybeTupleToUnion<T['by']>,
      ByValid extends Has<ByFields, OrderFields>,
      HavingFields extends GetHavingFields<T['having']>,
      HavingValid extends Has<ByFields, HavingFields>,
      ByEmpty extends T['by'] extends never[] ? True : False,
      InputErrors extends ByEmpty extends True
      ? `Error: "by" must not be empty.`
      : HavingValid extends False
      ? {
          [P in HavingFields]: P extends ByFields
            ? never
            : P extends string
            ? `Error: Field "${P}" used in "having" needs to be provided in "by".`
            : [
                Error,
                'Field ',
                P,
                ` in "having" needs to be provided in "by"`,
              ]
        }[HavingFields]
      : 'take' extends Keys<T>
      ? 'orderBy' extends Keys<T>
        ? ByValid extends True
          ? {}
          : {
              [P in OrderFields]: P extends ByFields
                ? never
                : `Error: Field "${P}" in "orderBy" needs to be provided in "by"`
            }[OrderFields]
        : 'Error: If you provide "take", you also need to provide "orderBy"'
      : 'skip' extends Keys<T>
      ? 'orderBy' extends Keys<T>
        ? ByValid extends True
          ? {}
          : {
              [P in OrderFields]: P extends ByFields
                ? never
                : `Error: Field "${P}" in "orderBy" needs to be provided in "by"`
            }[OrderFields]
        : 'Error: If you provide "skip", you also need to provide "orderBy"'
      : ByValid extends True
      ? {}
      : {
          [P in OrderFields]: P extends ByFields
            ? never
            : `Error: Field "${P}" in "orderBy" needs to be provided in "by"`
        }[OrderFields]
    >(args: SubsetIntersection<T, ChildGroupByArgs, OrderByArg> & InputErrors): {} extends InputErrors ? GetChildGroupByPayload<T> : Prisma.PrismaPromise<InputErrors>
  /**
   * Fields of the Child model
   */
  readonly fields: ChildFieldRefs;
  }

  /**
   * The delegate class that acts as a "Promise-like" for Child.
   * Why is this prefixed with `Prisma__`?
   * Because we want to prevent naming conflicts as mentioned in
   * https://github.com/prisma/prisma-client-js/issues/707
   */
  export interface Prisma__ChildClient<T, Null = never, ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs, GlobalOmitOptions = {}> extends Prisma.PrismaPromise<T> {
    readonly [Symbol.toStringTag]: "PrismaPromise"
    family<T extends FamilyDefaultArgs<ExtArgs> = {}>(args?: Subset<T, FamilyDefaultArgs<ExtArgs>>): Prisma__FamilyClient<$Result.GetResult<Prisma.$FamilyPayload<ExtArgs>, T, "findUniqueOrThrow", GlobalOmitOptions> | Null, Null, ExtArgs, GlobalOmitOptions>
    checkInRecords<T extends Child$checkInRecordsArgs<ExtArgs> = {}>(args?: Subset<T, Child$checkInRecordsArgs<ExtArgs>>): Prisma.PrismaPromise<$Result.GetResult<Prisma.$CheckInRecordPayload<ExtArgs>, T, "findMany", GlobalOmitOptions> | Null>
    tickets<T extends Child$ticketsArgs<ExtArgs> = {}>(args?: Subset<T, Child$ticketsArgs<ExtArgs>>): Prisma.PrismaPromise<$Result.GetResult<Prisma.$TicketPayload<ExtArgs>, T, "findMany", GlobalOmitOptions> | Null>
    /**
     * Attaches callbacks for the resolution and/or rejection of the Promise.
     * @param onfulfilled The callback to execute when the Promise is resolved.
     * @param onrejected The callback to execute when the Promise is rejected.
     * @returns A Promise for the completion of which ever callback is executed.
     */
    then<TResult1 = T, TResult2 = never>(onfulfilled?: ((value: T) => TResult1 | PromiseLike<TResult1>) | undefined | null, onrejected?: ((reason: any) => TResult2 | PromiseLike<TResult2>) | undefined | null): $Utils.JsPromise<TResult1 | TResult2>
    /**
     * Attaches a callback for only the rejection of the Promise.
     * @param onrejected The callback to execute when the Promise is rejected.
     * @returns A Promise for the completion of the callback.
     */
    catch<TResult = never>(onrejected?: ((reason: any) => TResult | PromiseLike<TResult>) | undefined | null): $Utils.JsPromise<T | TResult>
    /**
     * Attaches a callback that is invoked when the Promise is settled (fulfilled or rejected). The
     * resolved value cannot be modified from the callback.
     * @param onfinally The callback to execute when the Promise is settled (fulfilled or rejected).
     * @returns A Promise for the completion of the callback.
     */
    finally(onfinally?: (() => void) | undefined | null): $Utils.JsPromise<T>
  }




  /**
   * Fields of the Child model
   */
  interface ChildFieldRefs {
    readonly id: FieldRef<"Child", 'String'>
    readonly firstName: FieldRef<"Child", 'String'>
    readonly lastName: FieldRef<"Child", 'String'>
    readonly birthdate: FieldRef<"Child", 'DateTime'>
    readonly allergies: FieldRef<"Child", 'String'>
    readonly notes: FieldRef<"Child", 'String'>
    readonly qrToken: FieldRef<"Child", 'String'>
    readonly lastParticipationDate: FieldRef<"Child", 'DateTime'>
    readonly familyId: FieldRef<"Child", 'String'>
  }
    

  // Custom InputTypes
  /**
   * Child findUnique
   */
  export type ChildFindUniqueArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Child
     */
    select?: ChildSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Child
     */
    omit?: ChildOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: ChildInclude<ExtArgs> | null
    /**
     * Filter, which Child to fetch.
     */
    where: ChildWhereUniqueInput
  }

  /**
   * Child findUniqueOrThrow
   */
  export type ChildFindUniqueOrThrowArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Child
     */
    select?: ChildSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Child
     */
    omit?: ChildOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: ChildInclude<ExtArgs> | null
    /**
     * Filter, which Child to fetch.
     */
    where: ChildWhereUniqueInput
  }

  /**
   * Child findFirst
   */
  export type ChildFindFirstArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Child
     */
    select?: ChildSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Child
     */
    omit?: ChildOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: ChildInclude<ExtArgs> | null
    /**
     * Filter, which Child to fetch.
     */
    where?: ChildWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of Children to fetch.
     */
    orderBy?: ChildOrderByWithRelationInput | ChildOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the position for searching for Children.
     */
    cursor?: ChildWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` Children from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` Children.
     */
    skip?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/distinct Distinct Docs}
     * 
     * Filter by unique combinations of Children.
     */
    distinct?: ChildScalarFieldEnum | ChildScalarFieldEnum[]
  }

  /**
   * Child findFirstOrThrow
   */
  export type ChildFindFirstOrThrowArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Child
     */
    select?: ChildSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Child
     */
    omit?: ChildOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: ChildInclude<ExtArgs> | null
    /**
     * Filter, which Child to fetch.
     */
    where?: ChildWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of Children to fetch.
     */
    orderBy?: ChildOrderByWithRelationInput | ChildOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the position for searching for Children.
     */
    cursor?: ChildWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` Children from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` Children.
     */
    skip?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/distinct Distinct Docs}
     * 
     * Filter by unique combinations of Children.
     */
    distinct?: ChildScalarFieldEnum | ChildScalarFieldEnum[]
  }

  /**
   * Child findMany
   */
  export type ChildFindManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Child
     */
    select?: ChildSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Child
     */
    omit?: ChildOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: ChildInclude<ExtArgs> | null
    /**
     * Filter, which Children to fetch.
     */
    where?: ChildWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of Children to fetch.
     */
    orderBy?: ChildOrderByWithRelationInput | ChildOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the position for listing Children.
     */
    cursor?: ChildWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` Children from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` Children.
     */
    skip?: number
    distinct?: ChildScalarFieldEnum | ChildScalarFieldEnum[]
  }

  /**
   * Child create
   */
  export type ChildCreateArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Child
     */
    select?: ChildSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Child
     */
    omit?: ChildOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: ChildInclude<ExtArgs> | null
    /**
     * The data needed to create a Child.
     */
    data: XOR<ChildCreateInput, ChildUncheckedCreateInput>
  }

  /**
   * Child createMany
   */
  export type ChildCreateManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * The data used to create many Children.
     */
    data: ChildCreateManyInput | ChildCreateManyInput[]
    skipDuplicates?: boolean
  }

  /**
   * Child createManyAndReturn
   */
  export type ChildCreateManyAndReturnArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Child
     */
    select?: ChildSelectCreateManyAndReturn<ExtArgs> | null
    /**
     * Omit specific fields from the Child
     */
    omit?: ChildOmit<ExtArgs> | null
    /**
     * The data used to create many Children.
     */
    data: ChildCreateManyInput | ChildCreateManyInput[]
    skipDuplicates?: boolean
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: ChildIncludeCreateManyAndReturn<ExtArgs> | null
  }

  /**
   * Child update
   */
  export type ChildUpdateArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Child
     */
    select?: ChildSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Child
     */
    omit?: ChildOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: ChildInclude<ExtArgs> | null
    /**
     * The data needed to update a Child.
     */
    data: XOR<ChildUpdateInput, ChildUncheckedUpdateInput>
    /**
     * Choose, which Child to update.
     */
    where: ChildWhereUniqueInput
  }

  /**
   * Child updateMany
   */
  export type ChildUpdateManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * The data used to update Children.
     */
    data: XOR<ChildUpdateManyMutationInput, ChildUncheckedUpdateManyInput>
    /**
     * Filter which Children to update
     */
    where?: ChildWhereInput
    /**
     * Limit how many Children to update.
     */
    limit?: number
  }

  /**
   * Child updateManyAndReturn
   */
  export type ChildUpdateManyAndReturnArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Child
     */
    select?: ChildSelectUpdateManyAndReturn<ExtArgs> | null
    /**
     * Omit specific fields from the Child
     */
    omit?: ChildOmit<ExtArgs> | null
    /**
     * The data used to update Children.
     */
    data: XOR<ChildUpdateManyMutationInput, ChildUncheckedUpdateManyInput>
    /**
     * Filter which Children to update
     */
    where?: ChildWhereInput
    /**
     * Limit how many Children to update.
     */
    limit?: number
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: ChildIncludeUpdateManyAndReturn<ExtArgs> | null
  }

  /**
   * Child upsert
   */
  export type ChildUpsertArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Child
     */
    select?: ChildSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Child
     */
    omit?: ChildOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: ChildInclude<ExtArgs> | null
    /**
     * The filter to search for the Child to update in case it exists.
     */
    where: ChildWhereUniqueInput
    /**
     * In case the Child found by the `where` argument doesn't exist, create a new Child with this data.
     */
    create: XOR<ChildCreateInput, ChildUncheckedCreateInput>
    /**
     * In case the Child was found with the provided `where` argument, update it with this data.
     */
    update: XOR<ChildUpdateInput, ChildUncheckedUpdateInput>
  }

  /**
   * Child delete
   */
  export type ChildDeleteArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Child
     */
    select?: ChildSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Child
     */
    omit?: ChildOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: ChildInclude<ExtArgs> | null
    /**
     * Filter which Child to delete.
     */
    where: ChildWhereUniqueInput
  }

  /**
   * Child deleteMany
   */
  export type ChildDeleteManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Filter which Children to delete
     */
    where?: ChildWhereInput
    /**
     * Limit how many Children to delete.
     */
    limit?: number
  }

  /**
   * Child.checkInRecords
   */
  export type Child$checkInRecordsArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the CheckInRecord
     */
    select?: CheckInRecordSelect<ExtArgs> | null
    /**
     * Omit specific fields from the CheckInRecord
     */
    omit?: CheckInRecordOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: CheckInRecordInclude<ExtArgs> | null
    where?: CheckInRecordWhereInput
    orderBy?: CheckInRecordOrderByWithRelationInput | CheckInRecordOrderByWithRelationInput[]
    cursor?: CheckInRecordWhereUniqueInput
    take?: number
    skip?: number
    distinct?: CheckInRecordScalarFieldEnum | CheckInRecordScalarFieldEnum[]
  }

  /**
   * Child.tickets
   */
  export type Child$ticketsArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Ticket
     */
    select?: TicketSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Ticket
     */
    omit?: TicketOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: TicketInclude<ExtArgs> | null
    where?: TicketWhereInput
    orderBy?: TicketOrderByWithRelationInput | TicketOrderByWithRelationInput[]
    cursor?: TicketWhereUniqueInput
    take?: number
    skip?: number
    distinct?: TicketScalarFieldEnum | TicketScalarFieldEnum[]
  }

  /**
   * Child without action
   */
  export type ChildDefaultArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Child
     */
    select?: ChildSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Child
     */
    omit?: ChildOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: ChildInclude<ExtArgs> | null
  }


  /**
   * Model Event
   */

  export type AggregateEvent = {
    _count: EventCountAggregateOutputType | null
    _min: EventMinAggregateOutputType | null
    _max: EventMaxAggregateOutputType | null
  }

  export type EventMinAggregateOutputType = {
    id: string | null
    name: string | null
    startDate: Date | null
    endDate: Date | null
  }

  export type EventMaxAggregateOutputType = {
    id: string | null
    name: string | null
    startDate: Date | null
    endDate: Date | null
  }

  export type EventCountAggregateOutputType = {
    id: number
    name: number
    startDate: number
    endDate: number
    _all: number
  }


  export type EventMinAggregateInputType = {
    id?: true
    name?: true
    startDate?: true
    endDate?: true
  }

  export type EventMaxAggregateInputType = {
    id?: true
    name?: true
    startDate?: true
    endDate?: true
  }

  export type EventCountAggregateInputType = {
    id?: true
    name?: true
    startDate?: true
    endDate?: true
    _all?: true
  }

  export type EventAggregateArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Filter which Event to aggregate.
     */
    where?: EventWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of Events to fetch.
     */
    orderBy?: EventOrderByWithRelationInput | EventOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the start position
     */
    cursor?: EventWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` Events from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` Events.
     */
    skip?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/aggregations Aggregation Docs}
     * 
     * Count returned Events
    **/
    _count?: true | EventCountAggregateInputType
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/aggregations Aggregation Docs}
     * 
     * Select which fields to find the minimum value
    **/
    _min?: EventMinAggregateInputType
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/aggregations Aggregation Docs}
     * 
     * Select which fields to find the maximum value
    **/
    _max?: EventMaxAggregateInputType
  }

  export type GetEventAggregateType<T extends EventAggregateArgs> = {
        [P in keyof T & keyof AggregateEvent]: P extends '_count' | 'count'
      ? T[P] extends true
        ? number
        : GetScalarType<T[P], AggregateEvent[P]>
      : GetScalarType<T[P], AggregateEvent[P]>
  }




  export type EventGroupByArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    where?: EventWhereInput
    orderBy?: EventOrderByWithAggregationInput | EventOrderByWithAggregationInput[]
    by: EventScalarFieldEnum[] | EventScalarFieldEnum
    having?: EventScalarWhereWithAggregatesInput
    take?: number
    skip?: number
    _count?: EventCountAggregateInputType | true
    _min?: EventMinAggregateInputType
    _max?: EventMaxAggregateInputType
  }

  export type EventGroupByOutputType = {
    id: string
    name: string
    startDate: Date
    endDate: Date
    _count: EventCountAggregateOutputType | null
    _min: EventMinAggregateOutputType | null
    _max: EventMaxAggregateOutputType | null
  }

  type GetEventGroupByPayload<T extends EventGroupByArgs> = Prisma.PrismaPromise<
    Array<
      PickEnumerable<EventGroupByOutputType, T['by']> &
        {
          [P in ((keyof T) & (keyof EventGroupByOutputType))]: P extends '_count'
            ? T[P] extends boolean
              ? number
              : GetScalarType<T[P], EventGroupByOutputType[P]>
            : GetScalarType<T[P], EventGroupByOutputType[P]>
        }
      >
    >


  export type EventSelect<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetSelect<{
    id?: boolean
    name?: boolean
    startDate?: boolean
    endDate?: boolean
    sessions?: boolean | Event$sessionsArgs<ExtArgs>
    _count?: boolean | EventCountOutputTypeDefaultArgs<ExtArgs>
  }, ExtArgs["result"]["event"]>

  export type EventSelectCreateManyAndReturn<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetSelect<{
    id?: boolean
    name?: boolean
    startDate?: boolean
    endDate?: boolean
  }, ExtArgs["result"]["event"]>

  export type EventSelectUpdateManyAndReturn<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetSelect<{
    id?: boolean
    name?: boolean
    startDate?: boolean
    endDate?: boolean
  }, ExtArgs["result"]["event"]>

  export type EventSelectScalar = {
    id?: boolean
    name?: boolean
    startDate?: boolean
    endDate?: boolean
  }

  export type EventOmit<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetOmit<"id" | "name" | "startDate" | "endDate", ExtArgs["result"]["event"]>
  export type EventInclude<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    sessions?: boolean | Event$sessionsArgs<ExtArgs>
    _count?: boolean | EventCountOutputTypeDefaultArgs<ExtArgs>
  }
  export type EventIncludeCreateManyAndReturn<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {}
  export type EventIncludeUpdateManyAndReturn<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {}

  export type $EventPayload<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    name: "Event"
    objects: {
      sessions: Prisma.$SessionPayload<ExtArgs>[]
    }
    scalars: $Extensions.GetPayloadResult<{
      id: string
      name: string
      startDate: Date
      endDate: Date
    }, ExtArgs["result"]["event"]>
    composites: {}
  }

  type EventGetPayload<S extends boolean | null | undefined | EventDefaultArgs> = $Result.GetResult<Prisma.$EventPayload, S>

  type EventCountArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> =
    Omit<EventFindManyArgs, 'select' | 'include' | 'distinct' | 'omit'> & {
      select?: EventCountAggregateInputType | true
    }

  export interface EventDelegate<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs, GlobalOmitOptions = {}> {
    [K: symbol]: { types: Prisma.TypeMap<ExtArgs>['model']['Event'], meta: { name: 'Event' } }
    /**
     * Find zero or one Event that matches the filter.
     * @param {EventFindUniqueArgs} args - Arguments to find a Event
     * @example
     * // Get one Event
     * const event = await prisma.event.findUnique({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findUnique<T extends EventFindUniqueArgs>(args: SelectSubset<T, EventFindUniqueArgs<ExtArgs>>): Prisma__EventClient<$Result.GetResult<Prisma.$EventPayload<ExtArgs>, T, "findUnique", GlobalOmitOptions> | null, null, ExtArgs, GlobalOmitOptions>

    /**
     * Find one Event that matches the filter or throw an error with `error.code='P2025'`
     * if no matches were found.
     * @param {EventFindUniqueOrThrowArgs} args - Arguments to find a Event
     * @example
     * // Get one Event
     * const event = await prisma.event.findUniqueOrThrow({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findUniqueOrThrow<T extends EventFindUniqueOrThrowArgs>(args: SelectSubset<T, EventFindUniqueOrThrowArgs<ExtArgs>>): Prisma__EventClient<$Result.GetResult<Prisma.$EventPayload<ExtArgs>, T, "findUniqueOrThrow", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Find the first Event that matches the filter.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {EventFindFirstArgs} args - Arguments to find a Event
     * @example
     * // Get one Event
     * const event = await prisma.event.findFirst({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findFirst<T extends EventFindFirstArgs>(args?: SelectSubset<T, EventFindFirstArgs<ExtArgs>>): Prisma__EventClient<$Result.GetResult<Prisma.$EventPayload<ExtArgs>, T, "findFirst", GlobalOmitOptions> | null, null, ExtArgs, GlobalOmitOptions>

    /**
     * Find the first Event that matches the filter or
     * throw `PrismaKnownClientError` with `P2025` code if no matches were found.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {EventFindFirstOrThrowArgs} args - Arguments to find a Event
     * @example
     * // Get one Event
     * const event = await prisma.event.findFirstOrThrow({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findFirstOrThrow<T extends EventFindFirstOrThrowArgs>(args?: SelectSubset<T, EventFindFirstOrThrowArgs<ExtArgs>>): Prisma__EventClient<$Result.GetResult<Prisma.$EventPayload<ExtArgs>, T, "findFirstOrThrow", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Find zero or more Events that matches the filter.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {EventFindManyArgs} args - Arguments to filter and select certain fields only.
     * @example
     * // Get all Events
     * const events = await prisma.event.findMany()
     * 
     * // Get first 10 Events
     * const events = await prisma.event.findMany({ take: 10 })
     * 
     * // Only select the `id`
     * const eventWithIdOnly = await prisma.event.findMany({ select: { id: true } })
     * 
     */
    findMany<T extends EventFindManyArgs>(args?: SelectSubset<T, EventFindManyArgs<ExtArgs>>): Prisma.PrismaPromise<$Result.GetResult<Prisma.$EventPayload<ExtArgs>, T, "findMany", GlobalOmitOptions>>

    /**
     * Create a Event.
     * @param {EventCreateArgs} args - Arguments to create a Event.
     * @example
     * // Create one Event
     * const Event = await prisma.event.create({
     *   data: {
     *     // ... data to create a Event
     *   }
     * })
     * 
     */
    create<T extends EventCreateArgs>(args: SelectSubset<T, EventCreateArgs<ExtArgs>>): Prisma__EventClient<$Result.GetResult<Prisma.$EventPayload<ExtArgs>, T, "create", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Create many Events.
     * @param {EventCreateManyArgs} args - Arguments to create many Events.
     * @example
     * // Create many Events
     * const event = await prisma.event.createMany({
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     *     
     */
    createMany<T extends EventCreateManyArgs>(args?: SelectSubset<T, EventCreateManyArgs<ExtArgs>>): Prisma.PrismaPromise<BatchPayload>

    /**
     * Create many Events and returns the data saved in the database.
     * @param {EventCreateManyAndReturnArgs} args - Arguments to create many Events.
     * @example
     * // Create many Events
     * const event = await prisma.event.createManyAndReturn({
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * 
     * // Create many Events and only return the `id`
     * const eventWithIdOnly = await prisma.event.createManyAndReturn({
     *   select: { id: true },
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * 
     */
    createManyAndReturn<T extends EventCreateManyAndReturnArgs>(args?: SelectSubset<T, EventCreateManyAndReturnArgs<ExtArgs>>): Prisma.PrismaPromise<$Result.GetResult<Prisma.$EventPayload<ExtArgs>, T, "createManyAndReturn", GlobalOmitOptions>>

    /**
     * Delete a Event.
     * @param {EventDeleteArgs} args - Arguments to delete one Event.
     * @example
     * // Delete one Event
     * const Event = await prisma.event.delete({
     *   where: {
     *     // ... filter to delete one Event
     *   }
     * })
     * 
     */
    delete<T extends EventDeleteArgs>(args: SelectSubset<T, EventDeleteArgs<ExtArgs>>): Prisma__EventClient<$Result.GetResult<Prisma.$EventPayload<ExtArgs>, T, "delete", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Update one Event.
     * @param {EventUpdateArgs} args - Arguments to update one Event.
     * @example
     * // Update one Event
     * const event = await prisma.event.update({
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: {
     *     // ... provide data here
     *   }
     * })
     * 
     */
    update<T extends EventUpdateArgs>(args: SelectSubset<T, EventUpdateArgs<ExtArgs>>): Prisma__EventClient<$Result.GetResult<Prisma.$EventPayload<ExtArgs>, T, "update", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Delete zero or more Events.
     * @param {EventDeleteManyArgs} args - Arguments to filter Events to delete.
     * @example
     * // Delete a few Events
     * const { count } = await prisma.event.deleteMany({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     * 
     */
    deleteMany<T extends EventDeleteManyArgs>(args?: SelectSubset<T, EventDeleteManyArgs<ExtArgs>>): Prisma.PrismaPromise<BatchPayload>

    /**
     * Update zero or more Events.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {EventUpdateManyArgs} args - Arguments to update one or more rows.
     * @example
     * // Update many Events
     * const event = await prisma.event.updateMany({
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: {
     *     // ... provide data here
     *   }
     * })
     * 
     */
    updateMany<T extends EventUpdateManyArgs>(args: SelectSubset<T, EventUpdateManyArgs<ExtArgs>>): Prisma.PrismaPromise<BatchPayload>

    /**
     * Update zero or more Events and returns the data updated in the database.
     * @param {EventUpdateManyAndReturnArgs} args - Arguments to update many Events.
     * @example
     * // Update many Events
     * const event = await prisma.event.updateManyAndReturn({
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * 
     * // Update zero or more Events and only return the `id`
     * const eventWithIdOnly = await prisma.event.updateManyAndReturn({
     *   select: { id: true },
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * 
     */
    updateManyAndReturn<T extends EventUpdateManyAndReturnArgs>(args: SelectSubset<T, EventUpdateManyAndReturnArgs<ExtArgs>>): Prisma.PrismaPromise<$Result.GetResult<Prisma.$EventPayload<ExtArgs>, T, "updateManyAndReturn", GlobalOmitOptions>>

    /**
     * Create or update one Event.
     * @param {EventUpsertArgs} args - Arguments to update or create a Event.
     * @example
     * // Update or create a Event
     * const event = await prisma.event.upsert({
     *   create: {
     *     // ... data to create a Event
     *   },
     *   update: {
     *     // ... in case it already exists, update
     *   },
     *   where: {
     *     // ... the filter for the Event we want to update
     *   }
     * })
     */
    upsert<T extends EventUpsertArgs>(args: SelectSubset<T, EventUpsertArgs<ExtArgs>>): Prisma__EventClient<$Result.GetResult<Prisma.$EventPayload<ExtArgs>, T, "upsert", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>


    /**
     * Count the number of Events.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {EventCountArgs} args - Arguments to filter Events to count.
     * @example
     * // Count the number of Events
     * const count = await prisma.event.count({
     *   where: {
     *     // ... the filter for the Events we want to count
     *   }
     * })
    **/
    count<T extends EventCountArgs>(
      args?: Subset<T, EventCountArgs>,
    ): Prisma.PrismaPromise<
      T extends $Utils.Record<'select', any>
        ? T['select'] extends true
          ? number
          : GetScalarType<T['select'], EventCountAggregateOutputType>
        : number
    >

    /**
     * Allows you to perform aggregations operations on a Event.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {EventAggregateArgs} args - Select which aggregations you would like to apply and on what fields.
     * @example
     * // Ordered by age ascending
     * // Where email contains prisma.io
     * // Limited to the 10 users
     * const aggregations = await prisma.user.aggregate({
     *   _avg: {
     *     age: true,
     *   },
     *   where: {
     *     email: {
     *       contains: "prisma.io",
     *     },
     *   },
     *   orderBy: {
     *     age: "asc",
     *   },
     *   take: 10,
     * })
    **/
    aggregate<T extends EventAggregateArgs>(args: Subset<T, EventAggregateArgs>): Prisma.PrismaPromise<GetEventAggregateType<T>>

    /**
     * Group by Event.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {EventGroupByArgs} args - Group by arguments.
     * @example
     * // Group by city, order by createdAt, get count
     * const result = await prisma.user.groupBy({
     *   by: ['city', 'createdAt'],
     *   orderBy: {
     *     createdAt: true
     *   },
     *   _count: {
     *     _all: true
     *   },
     * })
     * 
    **/
    groupBy<
      T extends EventGroupByArgs,
      HasSelectOrTake extends Or<
        Extends<'skip', Keys<T>>,
        Extends<'take', Keys<T>>
      >,
      OrderByArg extends True extends HasSelectOrTake
        ? { orderBy: EventGroupByArgs['orderBy'] }
        : { orderBy?: EventGroupByArgs['orderBy'] },
      OrderFields extends ExcludeUnderscoreKeys<Keys<MaybeTupleToUnion<T['orderBy']>>>,
      ByFields extends MaybeTupleToUnion<T['by']>,
      ByValid extends Has<ByFields, OrderFields>,
      HavingFields extends GetHavingFields<T['having']>,
      HavingValid extends Has<ByFields, HavingFields>,
      ByEmpty extends T['by'] extends never[] ? True : False,
      InputErrors extends ByEmpty extends True
      ? `Error: "by" must not be empty.`
      : HavingValid extends False
      ? {
          [P in HavingFields]: P extends ByFields
            ? never
            : P extends string
            ? `Error: Field "${P}" used in "having" needs to be provided in "by".`
            : [
                Error,
                'Field ',
                P,
                ` in "having" needs to be provided in "by"`,
              ]
        }[HavingFields]
      : 'take' extends Keys<T>
      ? 'orderBy' extends Keys<T>
        ? ByValid extends True
          ? {}
          : {
              [P in OrderFields]: P extends ByFields
                ? never
                : `Error: Field "${P}" in "orderBy" needs to be provided in "by"`
            }[OrderFields]
        : 'Error: If you provide "take", you also need to provide "orderBy"'
      : 'skip' extends Keys<T>
      ? 'orderBy' extends Keys<T>
        ? ByValid extends True
          ? {}
          : {
              [P in OrderFields]: P extends ByFields
                ? never
                : `Error: Field "${P}" in "orderBy" needs to be provided in "by"`
            }[OrderFields]
        : 'Error: If you provide "skip", you also need to provide "orderBy"'
      : ByValid extends True
      ? {}
      : {
          [P in OrderFields]: P extends ByFields
            ? never
            : `Error: Field "${P}" in "orderBy" needs to be provided in "by"`
        }[OrderFields]
    >(args: SubsetIntersection<T, EventGroupByArgs, OrderByArg> & InputErrors): {} extends InputErrors ? GetEventGroupByPayload<T> : Prisma.PrismaPromise<InputErrors>
  /**
   * Fields of the Event model
   */
  readonly fields: EventFieldRefs;
  }

  /**
   * The delegate class that acts as a "Promise-like" for Event.
   * Why is this prefixed with `Prisma__`?
   * Because we want to prevent naming conflicts as mentioned in
   * https://github.com/prisma/prisma-client-js/issues/707
   */
  export interface Prisma__EventClient<T, Null = never, ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs, GlobalOmitOptions = {}> extends Prisma.PrismaPromise<T> {
    readonly [Symbol.toStringTag]: "PrismaPromise"
    sessions<T extends Event$sessionsArgs<ExtArgs> = {}>(args?: Subset<T, Event$sessionsArgs<ExtArgs>>): Prisma.PrismaPromise<$Result.GetResult<Prisma.$SessionPayload<ExtArgs>, T, "findMany", GlobalOmitOptions> | Null>
    /**
     * Attaches callbacks for the resolution and/or rejection of the Promise.
     * @param onfulfilled The callback to execute when the Promise is resolved.
     * @param onrejected The callback to execute when the Promise is rejected.
     * @returns A Promise for the completion of which ever callback is executed.
     */
    then<TResult1 = T, TResult2 = never>(onfulfilled?: ((value: T) => TResult1 | PromiseLike<TResult1>) | undefined | null, onrejected?: ((reason: any) => TResult2 | PromiseLike<TResult2>) | undefined | null): $Utils.JsPromise<TResult1 | TResult2>
    /**
     * Attaches a callback for only the rejection of the Promise.
     * @param onrejected The callback to execute when the Promise is rejected.
     * @returns A Promise for the completion of the callback.
     */
    catch<TResult = never>(onrejected?: ((reason: any) => TResult | PromiseLike<TResult>) | undefined | null): $Utils.JsPromise<T | TResult>
    /**
     * Attaches a callback that is invoked when the Promise is settled (fulfilled or rejected). The
     * resolved value cannot be modified from the callback.
     * @param onfinally The callback to execute when the Promise is settled (fulfilled or rejected).
     * @returns A Promise for the completion of the callback.
     */
    finally(onfinally?: (() => void) | undefined | null): $Utils.JsPromise<T>
  }




  /**
   * Fields of the Event model
   */
  interface EventFieldRefs {
    readonly id: FieldRef<"Event", 'String'>
    readonly name: FieldRef<"Event", 'String'>
    readonly startDate: FieldRef<"Event", 'DateTime'>
    readonly endDate: FieldRef<"Event", 'DateTime'>
  }
    

  // Custom InputTypes
  /**
   * Event findUnique
   */
  export type EventFindUniqueArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Event
     */
    select?: EventSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Event
     */
    omit?: EventOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: EventInclude<ExtArgs> | null
    /**
     * Filter, which Event to fetch.
     */
    where: EventWhereUniqueInput
  }

  /**
   * Event findUniqueOrThrow
   */
  export type EventFindUniqueOrThrowArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Event
     */
    select?: EventSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Event
     */
    omit?: EventOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: EventInclude<ExtArgs> | null
    /**
     * Filter, which Event to fetch.
     */
    where: EventWhereUniqueInput
  }

  /**
   * Event findFirst
   */
  export type EventFindFirstArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Event
     */
    select?: EventSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Event
     */
    omit?: EventOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: EventInclude<ExtArgs> | null
    /**
     * Filter, which Event to fetch.
     */
    where?: EventWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of Events to fetch.
     */
    orderBy?: EventOrderByWithRelationInput | EventOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the position for searching for Events.
     */
    cursor?: EventWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` Events from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` Events.
     */
    skip?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/distinct Distinct Docs}
     * 
     * Filter by unique combinations of Events.
     */
    distinct?: EventScalarFieldEnum | EventScalarFieldEnum[]
  }

  /**
   * Event findFirstOrThrow
   */
  export type EventFindFirstOrThrowArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Event
     */
    select?: EventSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Event
     */
    omit?: EventOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: EventInclude<ExtArgs> | null
    /**
     * Filter, which Event to fetch.
     */
    where?: EventWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of Events to fetch.
     */
    orderBy?: EventOrderByWithRelationInput | EventOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the position for searching for Events.
     */
    cursor?: EventWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` Events from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` Events.
     */
    skip?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/distinct Distinct Docs}
     * 
     * Filter by unique combinations of Events.
     */
    distinct?: EventScalarFieldEnum | EventScalarFieldEnum[]
  }

  /**
   * Event findMany
   */
  export type EventFindManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Event
     */
    select?: EventSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Event
     */
    omit?: EventOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: EventInclude<ExtArgs> | null
    /**
     * Filter, which Events to fetch.
     */
    where?: EventWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of Events to fetch.
     */
    orderBy?: EventOrderByWithRelationInput | EventOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the position for listing Events.
     */
    cursor?: EventWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` Events from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` Events.
     */
    skip?: number
    distinct?: EventScalarFieldEnum | EventScalarFieldEnum[]
  }

  /**
   * Event create
   */
  export type EventCreateArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Event
     */
    select?: EventSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Event
     */
    omit?: EventOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: EventInclude<ExtArgs> | null
    /**
     * The data needed to create a Event.
     */
    data: XOR<EventCreateInput, EventUncheckedCreateInput>
  }

  /**
   * Event createMany
   */
  export type EventCreateManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * The data used to create many Events.
     */
    data: EventCreateManyInput | EventCreateManyInput[]
    skipDuplicates?: boolean
  }

  /**
   * Event createManyAndReturn
   */
  export type EventCreateManyAndReturnArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Event
     */
    select?: EventSelectCreateManyAndReturn<ExtArgs> | null
    /**
     * Omit specific fields from the Event
     */
    omit?: EventOmit<ExtArgs> | null
    /**
     * The data used to create many Events.
     */
    data: EventCreateManyInput | EventCreateManyInput[]
    skipDuplicates?: boolean
  }

  /**
   * Event update
   */
  export type EventUpdateArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Event
     */
    select?: EventSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Event
     */
    omit?: EventOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: EventInclude<ExtArgs> | null
    /**
     * The data needed to update a Event.
     */
    data: XOR<EventUpdateInput, EventUncheckedUpdateInput>
    /**
     * Choose, which Event to update.
     */
    where: EventWhereUniqueInput
  }

  /**
   * Event updateMany
   */
  export type EventUpdateManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * The data used to update Events.
     */
    data: XOR<EventUpdateManyMutationInput, EventUncheckedUpdateManyInput>
    /**
     * Filter which Events to update
     */
    where?: EventWhereInput
    /**
     * Limit how many Events to update.
     */
    limit?: number
  }

  /**
   * Event updateManyAndReturn
   */
  export type EventUpdateManyAndReturnArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Event
     */
    select?: EventSelectUpdateManyAndReturn<ExtArgs> | null
    /**
     * Omit specific fields from the Event
     */
    omit?: EventOmit<ExtArgs> | null
    /**
     * The data used to update Events.
     */
    data: XOR<EventUpdateManyMutationInput, EventUncheckedUpdateManyInput>
    /**
     * Filter which Events to update
     */
    where?: EventWhereInput
    /**
     * Limit how many Events to update.
     */
    limit?: number
  }

  /**
   * Event upsert
   */
  export type EventUpsertArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Event
     */
    select?: EventSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Event
     */
    omit?: EventOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: EventInclude<ExtArgs> | null
    /**
     * The filter to search for the Event to update in case it exists.
     */
    where: EventWhereUniqueInput
    /**
     * In case the Event found by the `where` argument doesn't exist, create a new Event with this data.
     */
    create: XOR<EventCreateInput, EventUncheckedCreateInput>
    /**
     * In case the Event was found with the provided `where` argument, update it with this data.
     */
    update: XOR<EventUpdateInput, EventUncheckedUpdateInput>
  }

  /**
   * Event delete
   */
  export type EventDeleteArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Event
     */
    select?: EventSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Event
     */
    omit?: EventOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: EventInclude<ExtArgs> | null
    /**
     * Filter which Event to delete.
     */
    where: EventWhereUniqueInput
  }

  /**
   * Event deleteMany
   */
  export type EventDeleteManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Filter which Events to delete
     */
    where?: EventWhereInput
    /**
     * Limit how many Events to delete.
     */
    limit?: number
  }

  /**
   * Event.sessions
   */
  export type Event$sessionsArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Session
     */
    select?: SessionSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Session
     */
    omit?: SessionOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: SessionInclude<ExtArgs> | null
    where?: SessionWhereInput
    orderBy?: SessionOrderByWithRelationInput | SessionOrderByWithRelationInput[]
    cursor?: SessionWhereUniqueInput
    take?: number
    skip?: number
    distinct?: SessionScalarFieldEnum | SessionScalarFieldEnum[]
  }

  /**
   * Event without action
   */
  export type EventDefaultArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Event
     */
    select?: EventSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Event
     */
    omit?: EventOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: EventInclude<ExtArgs> | null
  }


  /**
   * Model Session
   */

  export type AggregateSession = {
    _count: SessionCountAggregateOutputType | null
    _min: SessionMinAggregateOutputType | null
    _max: SessionMaxAggregateOutputType | null
  }

  export type SessionMinAggregateOutputType = {
    id: string | null
    name: string | null
    startTime: Date | null
    endTime: Date | null
    isActive: boolean | null
    requiresTicket: boolean | null
    eventId: string | null
  }

  export type SessionMaxAggregateOutputType = {
    id: string | null
    name: string | null
    startTime: Date | null
    endTime: Date | null
    isActive: boolean | null
    requiresTicket: boolean | null
    eventId: string | null
  }

  export type SessionCountAggregateOutputType = {
    id: number
    name: number
    startTime: number
    endTime: number
    isActive: number
    requiresTicket: number
    eventId: number
    _all: number
  }


  export type SessionMinAggregateInputType = {
    id?: true
    name?: true
    startTime?: true
    endTime?: true
    isActive?: true
    requiresTicket?: true
    eventId?: true
  }

  export type SessionMaxAggregateInputType = {
    id?: true
    name?: true
    startTime?: true
    endTime?: true
    isActive?: true
    requiresTicket?: true
    eventId?: true
  }

  export type SessionCountAggregateInputType = {
    id?: true
    name?: true
    startTime?: true
    endTime?: true
    isActive?: true
    requiresTicket?: true
    eventId?: true
    _all?: true
  }

  export type SessionAggregateArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Filter which Session to aggregate.
     */
    where?: SessionWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of Sessions to fetch.
     */
    orderBy?: SessionOrderByWithRelationInput | SessionOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the start position
     */
    cursor?: SessionWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` Sessions from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` Sessions.
     */
    skip?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/aggregations Aggregation Docs}
     * 
     * Count returned Sessions
    **/
    _count?: true | SessionCountAggregateInputType
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/aggregations Aggregation Docs}
     * 
     * Select which fields to find the minimum value
    **/
    _min?: SessionMinAggregateInputType
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/aggregations Aggregation Docs}
     * 
     * Select which fields to find the maximum value
    **/
    _max?: SessionMaxAggregateInputType
  }

  export type GetSessionAggregateType<T extends SessionAggregateArgs> = {
        [P in keyof T & keyof AggregateSession]: P extends '_count' | 'count'
      ? T[P] extends true
        ? number
        : GetScalarType<T[P], AggregateSession[P]>
      : GetScalarType<T[P], AggregateSession[P]>
  }




  export type SessionGroupByArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    where?: SessionWhereInput
    orderBy?: SessionOrderByWithAggregationInput | SessionOrderByWithAggregationInput[]
    by: SessionScalarFieldEnum[] | SessionScalarFieldEnum
    having?: SessionScalarWhereWithAggregatesInput
    take?: number
    skip?: number
    _count?: SessionCountAggregateInputType | true
    _min?: SessionMinAggregateInputType
    _max?: SessionMaxAggregateInputType
  }

  export type SessionGroupByOutputType = {
    id: string
    name: string
    startTime: Date
    endTime: Date
    isActive: boolean
    requiresTicket: boolean
    eventId: string
    _count: SessionCountAggregateOutputType | null
    _min: SessionMinAggregateOutputType | null
    _max: SessionMaxAggregateOutputType | null
  }

  type GetSessionGroupByPayload<T extends SessionGroupByArgs> = Prisma.PrismaPromise<
    Array<
      PickEnumerable<SessionGroupByOutputType, T['by']> &
        {
          [P in ((keyof T) & (keyof SessionGroupByOutputType))]: P extends '_count'
            ? T[P] extends boolean
              ? number
              : GetScalarType<T[P], SessionGroupByOutputType[P]>
            : GetScalarType<T[P], SessionGroupByOutputType[P]>
        }
      >
    >


  export type SessionSelect<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetSelect<{
    id?: boolean
    name?: boolean
    startTime?: boolean
    endTime?: boolean
    isActive?: boolean
    requiresTicket?: boolean
    eventId?: boolean
    event?: boolean | EventDefaultArgs<ExtArgs>
    checkInRecords?: boolean | Session$checkInRecordsArgs<ExtArgs>
    tickets?: boolean | Session$ticketsArgs<ExtArgs>
    _count?: boolean | SessionCountOutputTypeDefaultArgs<ExtArgs>
  }, ExtArgs["result"]["session"]>

  export type SessionSelectCreateManyAndReturn<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetSelect<{
    id?: boolean
    name?: boolean
    startTime?: boolean
    endTime?: boolean
    isActive?: boolean
    requiresTicket?: boolean
    eventId?: boolean
    event?: boolean | EventDefaultArgs<ExtArgs>
  }, ExtArgs["result"]["session"]>

  export type SessionSelectUpdateManyAndReturn<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetSelect<{
    id?: boolean
    name?: boolean
    startTime?: boolean
    endTime?: boolean
    isActive?: boolean
    requiresTicket?: boolean
    eventId?: boolean
    event?: boolean | EventDefaultArgs<ExtArgs>
  }, ExtArgs["result"]["session"]>

  export type SessionSelectScalar = {
    id?: boolean
    name?: boolean
    startTime?: boolean
    endTime?: boolean
    isActive?: boolean
    requiresTicket?: boolean
    eventId?: boolean
  }

  export type SessionOmit<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetOmit<"id" | "name" | "startTime" | "endTime" | "isActive" | "requiresTicket" | "eventId", ExtArgs["result"]["session"]>
  export type SessionInclude<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    event?: boolean | EventDefaultArgs<ExtArgs>
    checkInRecords?: boolean | Session$checkInRecordsArgs<ExtArgs>
    tickets?: boolean | Session$ticketsArgs<ExtArgs>
    _count?: boolean | SessionCountOutputTypeDefaultArgs<ExtArgs>
  }
  export type SessionIncludeCreateManyAndReturn<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    event?: boolean | EventDefaultArgs<ExtArgs>
  }
  export type SessionIncludeUpdateManyAndReturn<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    event?: boolean | EventDefaultArgs<ExtArgs>
  }

  export type $SessionPayload<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    name: "Session"
    objects: {
      event: Prisma.$EventPayload<ExtArgs>
      checkInRecords: Prisma.$CheckInRecordPayload<ExtArgs>[]
      tickets: Prisma.$TicketPayload<ExtArgs>[]
    }
    scalars: $Extensions.GetPayloadResult<{
      id: string
      name: string
      startTime: Date
      endTime: Date
      isActive: boolean
      requiresTicket: boolean
      eventId: string
    }, ExtArgs["result"]["session"]>
    composites: {}
  }

  type SessionGetPayload<S extends boolean | null | undefined | SessionDefaultArgs> = $Result.GetResult<Prisma.$SessionPayload, S>

  type SessionCountArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> =
    Omit<SessionFindManyArgs, 'select' | 'include' | 'distinct' | 'omit'> & {
      select?: SessionCountAggregateInputType | true
    }

  export interface SessionDelegate<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs, GlobalOmitOptions = {}> {
    [K: symbol]: { types: Prisma.TypeMap<ExtArgs>['model']['Session'], meta: { name: 'Session' } }
    /**
     * Find zero or one Session that matches the filter.
     * @param {SessionFindUniqueArgs} args - Arguments to find a Session
     * @example
     * // Get one Session
     * const session = await prisma.session.findUnique({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findUnique<T extends SessionFindUniqueArgs>(args: SelectSubset<T, SessionFindUniqueArgs<ExtArgs>>): Prisma__SessionClient<$Result.GetResult<Prisma.$SessionPayload<ExtArgs>, T, "findUnique", GlobalOmitOptions> | null, null, ExtArgs, GlobalOmitOptions>

    /**
     * Find one Session that matches the filter or throw an error with `error.code='P2025'`
     * if no matches were found.
     * @param {SessionFindUniqueOrThrowArgs} args - Arguments to find a Session
     * @example
     * // Get one Session
     * const session = await prisma.session.findUniqueOrThrow({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findUniqueOrThrow<T extends SessionFindUniqueOrThrowArgs>(args: SelectSubset<T, SessionFindUniqueOrThrowArgs<ExtArgs>>): Prisma__SessionClient<$Result.GetResult<Prisma.$SessionPayload<ExtArgs>, T, "findUniqueOrThrow", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Find the first Session that matches the filter.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {SessionFindFirstArgs} args - Arguments to find a Session
     * @example
     * // Get one Session
     * const session = await prisma.session.findFirst({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findFirst<T extends SessionFindFirstArgs>(args?: SelectSubset<T, SessionFindFirstArgs<ExtArgs>>): Prisma__SessionClient<$Result.GetResult<Prisma.$SessionPayload<ExtArgs>, T, "findFirst", GlobalOmitOptions> | null, null, ExtArgs, GlobalOmitOptions>

    /**
     * Find the first Session that matches the filter or
     * throw `PrismaKnownClientError` with `P2025` code if no matches were found.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {SessionFindFirstOrThrowArgs} args - Arguments to find a Session
     * @example
     * // Get one Session
     * const session = await prisma.session.findFirstOrThrow({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findFirstOrThrow<T extends SessionFindFirstOrThrowArgs>(args?: SelectSubset<T, SessionFindFirstOrThrowArgs<ExtArgs>>): Prisma__SessionClient<$Result.GetResult<Prisma.$SessionPayload<ExtArgs>, T, "findFirstOrThrow", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Find zero or more Sessions that matches the filter.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {SessionFindManyArgs} args - Arguments to filter and select certain fields only.
     * @example
     * // Get all Sessions
     * const sessions = await prisma.session.findMany()
     * 
     * // Get first 10 Sessions
     * const sessions = await prisma.session.findMany({ take: 10 })
     * 
     * // Only select the `id`
     * const sessionWithIdOnly = await prisma.session.findMany({ select: { id: true } })
     * 
     */
    findMany<T extends SessionFindManyArgs>(args?: SelectSubset<T, SessionFindManyArgs<ExtArgs>>): Prisma.PrismaPromise<$Result.GetResult<Prisma.$SessionPayload<ExtArgs>, T, "findMany", GlobalOmitOptions>>

    /**
     * Create a Session.
     * @param {SessionCreateArgs} args - Arguments to create a Session.
     * @example
     * // Create one Session
     * const Session = await prisma.session.create({
     *   data: {
     *     // ... data to create a Session
     *   }
     * })
     * 
     */
    create<T extends SessionCreateArgs>(args: SelectSubset<T, SessionCreateArgs<ExtArgs>>): Prisma__SessionClient<$Result.GetResult<Prisma.$SessionPayload<ExtArgs>, T, "create", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Create many Sessions.
     * @param {SessionCreateManyArgs} args - Arguments to create many Sessions.
     * @example
     * // Create many Sessions
     * const session = await prisma.session.createMany({
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     *     
     */
    createMany<T extends SessionCreateManyArgs>(args?: SelectSubset<T, SessionCreateManyArgs<ExtArgs>>): Prisma.PrismaPromise<BatchPayload>

    /**
     * Create many Sessions and returns the data saved in the database.
     * @param {SessionCreateManyAndReturnArgs} args - Arguments to create many Sessions.
     * @example
     * // Create many Sessions
     * const session = await prisma.session.createManyAndReturn({
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * 
     * // Create many Sessions and only return the `id`
     * const sessionWithIdOnly = await prisma.session.createManyAndReturn({
     *   select: { id: true },
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * 
     */
    createManyAndReturn<T extends SessionCreateManyAndReturnArgs>(args?: SelectSubset<T, SessionCreateManyAndReturnArgs<ExtArgs>>): Prisma.PrismaPromise<$Result.GetResult<Prisma.$SessionPayload<ExtArgs>, T, "createManyAndReturn", GlobalOmitOptions>>

    /**
     * Delete a Session.
     * @param {SessionDeleteArgs} args - Arguments to delete one Session.
     * @example
     * // Delete one Session
     * const Session = await prisma.session.delete({
     *   where: {
     *     // ... filter to delete one Session
     *   }
     * })
     * 
     */
    delete<T extends SessionDeleteArgs>(args: SelectSubset<T, SessionDeleteArgs<ExtArgs>>): Prisma__SessionClient<$Result.GetResult<Prisma.$SessionPayload<ExtArgs>, T, "delete", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Update one Session.
     * @param {SessionUpdateArgs} args - Arguments to update one Session.
     * @example
     * // Update one Session
     * const session = await prisma.session.update({
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: {
     *     // ... provide data here
     *   }
     * })
     * 
     */
    update<T extends SessionUpdateArgs>(args: SelectSubset<T, SessionUpdateArgs<ExtArgs>>): Prisma__SessionClient<$Result.GetResult<Prisma.$SessionPayload<ExtArgs>, T, "update", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Delete zero or more Sessions.
     * @param {SessionDeleteManyArgs} args - Arguments to filter Sessions to delete.
     * @example
     * // Delete a few Sessions
     * const { count } = await prisma.session.deleteMany({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     * 
     */
    deleteMany<T extends SessionDeleteManyArgs>(args?: SelectSubset<T, SessionDeleteManyArgs<ExtArgs>>): Prisma.PrismaPromise<BatchPayload>

    /**
     * Update zero or more Sessions.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {SessionUpdateManyArgs} args - Arguments to update one or more rows.
     * @example
     * // Update many Sessions
     * const session = await prisma.session.updateMany({
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: {
     *     // ... provide data here
     *   }
     * })
     * 
     */
    updateMany<T extends SessionUpdateManyArgs>(args: SelectSubset<T, SessionUpdateManyArgs<ExtArgs>>): Prisma.PrismaPromise<BatchPayload>

    /**
     * Update zero or more Sessions and returns the data updated in the database.
     * @param {SessionUpdateManyAndReturnArgs} args - Arguments to update many Sessions.
     * @example
     * // Update many Sessions
     * const session = await prisma.session.updateManyAndReturn({
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * 
     * // Update zero or more Sessions and only return the `id`
     * const sessionWithIdOnly = await prisma.session.updateManyAndReturn({
     *   select: { id: true },
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * 
     */
    updateManyAndReturn<T extends SessionUpdateManyAndReturnArgs>(args: SelectSubset<T, SessionUpdateManyAndReturnArgs<ExtArgs>>): Prisma.PrismaPromise<$Result.GetResult<Prisma.$SessionPayload<ExtArgs>, T, "updateManyAndReturn", GlobalOmitOptions>>

    /**
     * Create or update one Session.
     * @param {SessionUpsertArgs} args - Arguments to update or create a Session.
     * @example
     * // Update or create a Session
     * const session = await prisma.session.upsert({
     *   create: {
     *     // ... data to create a Session
     *   },
     *   update: {
     *     // ... in case it already exists, update
     *   },
     *   where: {
     *     // ... the filter for the Session we want to update
     *   }
     * })
     */
    upsert<T extends SessionUpsertArgs>(args: SelectSubset<T, SessionUpsertArgs<ExtArgs>>): Prisma__SessionClient<$Result.GetResult<Prisma.$SessionPayload<ExtArgs>, T, "upsert", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>


    /**
     * Count the number of Sessions.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {SessionCountArgs} args - Arguments to filter Sessions to count.
     * @example
     * // Count the number of Sessions
     * const count = await prisma.session.count({
     *   where: {
     *     // ... the filter for the Sessions we want to count
     *   }
     * })
    **/
    count<T extends SessionCountArgs>(
      args?: Subset<T, SessionCountArgs>,
    ): Prisma.PrismaPromise<
      T extends $Utils.Record<'select', any>
        ? T['select'] extends true
          ? number
          : GetScalarType<T['select'], SessionCountAggregateOutputType>
        : number
    >

    /**
     * Allows you to perform aggregations operations on a Session.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {SessionAggregateArgs} args - Select which aggregations you would like to apply and on what fields.
     * @example
     * // Ordered by age ascending
     * // Where email contains prisma.io
     * // Limited to the 10 users
     * const aggregations = await prisma.user.aggregate({
     *   _avg: {
     *     age: true,
     *   },
     *   where: {
     *     email: {
     *       contains: "prisma.io",
     *     },
     *   },
     *   orderBy: {
     *     age: "asc",
     *   },
     *   take: 10,
     * })
    **/
    aggregate<T extends SessionAggregateArgs>(args: Subset<T, SessionAggregateArgs>): Prisma.PrismaPromise<GetSessionAggregateType<T>>

    /**
     * Group by Session.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {SessionGroupByArgs} args - Group by arguments.
     * @example
     * // Group by city, order by createdAt, get count
     * const result = await prisma.user.groupBy({
     *   by: ['city', 'createdAt'],
     *   orderBy: {
     *     createdAt: true
     *   },
     *   _count: {
     *     _all: true
     *   },
     * })
     * 
    **/
    groupBy<
      T extends SessionGroupByArgs,
      HasSelectOrTake extends Or<
        Extends<'skip', Keys<T>>,
        Extends<'take', Keys<T>>
      >,
      OrderByArg extends True extends HasSelectOrTake
        ? { orderBy: SessionGroupByArgs['orderBy'] }
        : { orderBy?: SessionGroupByArgs['orderBy'] },
      OrderFields extends ExcludeUnderscoreKeys<Keys<MaybeTupleToUnion<T['orderBy']>>>,
      ByFields extends MaybeTupleToUnion<T['by']>,
      ByValid extends Has<ByFields, OrderFields>,
      HavingFields extends GetHavingFields<T['having']>,
      HavingValid extends Has<ByFields, HavingFields>,
      ByEmpty extends T['by'] extends never[] ? True : False,
      InputErrors extends ByEmpty extends True
      ? `Error: "by" must not be empty.`
      : HavingValid extends False
      ? {
          [P in HavingFields]: P extends ByFields
            ? never
            : P extends string
            ? `Error: Field "${P}" used in "having" needs to be provided in "by".`
            : [
                Error,
                'Field ',
                P,
                ` in "having" needs to be provided in "by"`,
              ]
        }[HavingFields]
      : 'take' extends Keys<T>
      ? 'orderBy' extends Keys<T>
        ? ByValid extends True
          ? {}
          : {
              [P in OrderFields]: P extends ByFields
                ? never
                : `Error: Field "${P}" in "orderBy" needs to be provided in "by"`
            }[OrderFields]
        : 'Error: If you provide "take", you also need to provide "orderBy"'
      : 'skip' extends Keys<T>
      ? 'orderBy' extends Keys<T>
        ? ByValid extends True
          ? {}
          : {
              [P in OrderFields]: P extends ByFields
                ? never
                : `Error: Field "${P}" in "orderBy" needs to be provided in "by"`
            }[OrderFields]
        : 'Error: If you provide "skip", you also need to provide "orderBy"'
      : ByValid extends True
      ? {}
      : {
          [P in OrderFields]: P extends ByFields
            ? never
            : `Error: Field "${P}" in "orderBy" needs to be provided in "by"`
        }[OrderFields]
    >(args: SubsetIntersection<T, SessionGroupByArgs, OrderByArg> & InputErrors): {} extends InputErrors ? GetSessionGroupByPayload<T> : Prisma.PrismaPromise<InputErrors>
  /**
   * Fields of the Session model
   */
  readonly fields: SessionFieldRefs;
  }

  /**
   * The delegate class that acts as a "Promise-like" for Session.
   * Why is this prefixed with `Prisma__`?
   * Because we want to prevent naming conflicts as mentioned in
   * https://github.com/prisma/prisma-client-js/issues/707
   */
  export interface Prisma__SessionClient<T, Null = never, ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs, GlobalOmitOptions = {}> extends Prisma.PrismaPromise<T> {
    readonly [Symbol.toStringTag]: "PrismaPromise"
    event<T extends EventDefaultArgs<ExtArgs> = {}>(args?: Subset<T, EventDefaultArgs<ExtArgs>>): Prisma__EventClient<$Result.GetResult<Prisma.$EventPayload<ExtArgs>, T, "findUniqueOrThrow", GlobalOmitOptions> | Null, Null, ExtArgs, GlobalOmitOptions>
    checkInRecords<T extends Session$checkInRecordsArgs<ExtArgs> = {}>(args?: Subset<T, Session$checkInRecordsArgs<ExtArgs>>): Prisma.PrismaPromise<$Result.GetResult<Prisma.$CheckInRecordPayload<ExtArgs>, T, "findMany", GlobalOmitOptions> | Null>
    tickets<T extends Session$ticketsArgs<ExtArgs> = {}>(args?: Subset<T, Session$ticketsArgs<ExtArgs>>): Prisma.PrismaPromise<$Result.GetResult<Prisma.$TicketPayload<ExtArgs>, T, "findMany", GlobalOmitOptions> | Null>
    /**
     * Attaches callbacks for the resolution and/or rejection of the Promise.
     * @param onfulfilled The callback to execute when the Promise is resolved.
     * @param onrejected The callback to execute when the Promise is rejected.
     * @returns A Promise for the completion of which ever callback is executed.
     */
    then<TResult1 = T, TResult2 = never>(onfulfilled?: ((value: T) => TResult1 | PromiseLike<TResult1>) | undefined | null, onrejected?: ((reason: any) => TResult2 | PromiseLike<TResult2>) | undefined | null): $Utils.JsPromise<TResult1 | TResult2>
    /**
     * Attaches a callback for only the rejection of the Promise.
     * @param onrejected The callback to execute when the Promise is rejected.
     * @returns A Promise for the completion of the callback.
     */
    catch<TResult = never>(onrejected?: ((reason: any) => TResult | PromiseLike<TResult>) | undefined | null): $Utils.JsPromise<T | TResult>
    /**
     * Attaches a callback that is invoked when the Promise is settled (fulfilled or rejected). The
     * resolved value cannot be modified from the callback.
     * @param onfinally The callback to execute when the Promise is settled (fulfilled or rejected).
     * @returns A Promise for the completion of the callback.
     */
    finally(onfinally?: (() => void) | undefined | null): $Utils.JsPromise<T>
  }




  /**
   * Fields of the Session model
   */
  interface SessionFieldRefs {
    readonly id: FieldRef<"Session", 'String'>
    readonly name: FieldRef<"Session", 'String'>
    readonly startTime: FieldRef<"Session", 'DateTime'>
    readonly endTime: FieldRef<"Session", 'DateTime'>
    readonly isActive: FieldRef<"Session", 'Boolean'>
    readonly requiresTicket: FieldRef<"Session", 'Boolean'>
    readonly eventId: FieldRef<"Session", 'String'>
  }
    

  // Custom InputTypes
  /**
   * Session findUnique
   */
  export type SessionFindUniqueArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Session
     */
    select?: SessionSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Session
     */
    omit?: SessionOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: SessionInclude<ExtArgs> | null
    /**
     * Filter, which Session to fetch.
     */
    where: SessionWhereUniqueInput
  }

  /**
   * Session findUniqueOrThrow
   */
  export type SessionFindUniqueOrThrowArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Session
     */
    select?: SessionSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Session
     */
    omit?: SessionOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: SessionInclude<ExtArgs> | null
    /**
     * Filter, which Session to fetch.
     */
    where: SessionWhereUniqueInput
  }

  /**
   * Session findFirst
   */
  export type SessionFindFirstArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Session
     */
    select?: SessionSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Session
     */
    omit?: SessionOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: SessionInclude<ExtArgs> | null
    /**
     * Filter, which Session to fetch.
     */
    where?: SessionWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of Sessions to fetch.
     */
    orderBy?: SessionOrderByWithRelationInput | SessionOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the position for searching for Sessions.
     */
    cursor?: SessionWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` Sessions from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` Sessions.
     */
    skip?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/distinct Distinct Docs}
     * 
     * Filter by unique combinations of Sessions.
     */
    distinct?: SessionScalarFieldEnum | SessionScalarFieldEnum[]
  }

  /**
   * Session findFirstOrThrow
   */
  export type SessionFindFirstOrThrowArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Session
     */
    select?: SessionSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Session
     */
    omit?: SessionOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: SessionInclude<ExtArgs> | null
    /**
     * Filter, which Session to fetch.
     */
    where?: SessionWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of Sessions to fetch.
     */
    orderBy?: SessionOrderByWithRelationInput | SessionOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the position for searching for Sessions.
     */
    cursor?: SessionWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` Sessions from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` Sessions.
     */
    skip?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/distinct Distinct Docs}
     * 
     * Filter by unique combinations of Sessions.
     */
    distinct?: SessionScalarFieldEnum | SessionScalarFieldEnum[]
  }

  /**
   * Session findMany
   */
  export type SessionFindManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Session
     */
    select?: SessionSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Session
     */
    omit?: SessionOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: SessionInclude<ExtArgs> | null
    /**
     * Filter, which Sessions to fetch.
     */
    where?: SessionWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of Sessions to fetch.
     */
    orderBy?: SessionOrderByWithRelationInput | SessionOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the position for listing Sessions.
     */
    cursor?: SessionWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` Sessions from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` Sessions.
     */
    skip?: number
    distinct?: SessionScalarFieldEnum | SessionScalarFieldEnum[]
  }

  /**
   * Session create
   */
  export type SessionCreateArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Session
     */
    select?: SessionSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Session
     */
    omit?: SessionOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: SessionInclude<ExtArgs> | null
    /**
     * The data needed to create a Session.
     */
    data: XOR<SessionCreateInput, SessionUncheckedCreateInput>
  }

  /**
   * Session createMany
   */
  export type SessionCreateManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * The data used to create many Sessions.
     */
    data: SessionCreateManyInput | SessionCreateManyInput[]
    skipDuplicates?: boolean
  }

  /**
   * Session createManyAndReturn
   */
  export type SessionCreateManyAndReturnArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Session
     */
    select?: SessionSelectCreateManyAndReturn<ExtArgs> | null
    /**
     * Omit specific fields from the Session
     */
    omit?: SessionOmit<ExtArgs> | null
    /**
     * The data used to create many Sessions.
     */
    data: SessionCreateManyInput | SessionCreateManyInput[]
    skipDuplicates?: boolean
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: SessionIncludeCreateManyAndReturn<ExtArgs> | null
  }

  /**
   * Session update
   */
  export type SessionUpdateArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Session
     */
    select?: SessionSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Session
     */
    omit?: SessionOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: SessionInclude<ExtArgs> | null
    /**
     * The data needed to update a Session.
     */
    data: XOR<SessionUpdateInput, SessionUncheckedUpdateInput>
    /**
     * Choose, which Session to update.
     */
    where: SessionWhereUniqueInput
  }

  /**
   * Session updateMany
   */
  export type SessionUpdateManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * The data used to update Sessions.
     */
    data: XOR<SessionUpdateManyMutationInput, SessionUncheckedUpdateManyInput>
    /**
     * Filter which Sessions to update
     */
    where?: SessionWhereInput
    /**
     * Limit how many Sessions to update.
     */
    limit?: number
  }

  /**
   * Session updateManyAndReturn
   */
  export type SessionUpdateManyAndReturnArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Session
     */
    select?: SessionSelectUpdateManyAndReturn<ExtArgs> | null
    /**
     * Omit specific fields from the Session
     */
    omit?: SessionOmit<ExtArgs> | null
    /**
     * The data used to update Sessions.
     */
    data: XOR<SessionUpdateManyMutationInput, SessionUncheckedUpdateManyInput>
    /**
     * Filter which Sessions to update
     */
    where?: SessionWhereInput
    /**
     * Limit how many Sessions to update.
     */
    limit?: number
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: SessionIncludeUpdateManyAndReturn<ExtArgs> | null
  }

  /**
   * Session upsert
   */
  export type SessionUpsertArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Session
     */
    select?: SessionSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Session
     */
    omit?: SessionOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: SessionInclude<ExtArgs> | null
    /**
     * The filter to search for the Session to update in case it exists.
     */
    where: SessionWhereUniqueInput
    /**
     * In case the Session found by the `where` argument doesn't exist, create a new Session with this data.
     */
    create: XOR<SessionCreateInput, SessionUncheckedCreateInput>
    /**
     * In case the Session was found with the provided `where` argument, update it with this data.
     */
    update: XOR<SessionUpdateInput, SessionUncheckedUpdateInput>
  }

  /**
   * Session delete
   */
  export type SessionDeleteArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Session
     */
    select?: SessionSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Session
     */
    omit?: SessionOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: SessionInclude<ExtArgs> | null
    /**
     * Filter which Session to delete.
     */
    where: SessionWhereUniqueInput
  }

  /**
   * Session deleteMany
   */
  export type SessionDeleteManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Filter which Sessions to delete
     */
    where?: SessionWhereInput
    /**
     * Limit how many Sessions to delete.
     */
    limit?: number
  }

  /**
   * Session.checkInRecords
   */
  export type Session$checkInRecordsArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the CheckInRecord
     */
    select?: CheckInRecordSelect<ExtArgs> | null
    /**
     * Omit specific fields from the CheckInRecord
     */
    omit?: CheckInRecordOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: CheckInRecordInclude<ExtArgs> | null
    where?: CheckInRecordWhereInput
    orderBy?: CheckInRecordOrderByWithRelationInput | CheckInRecordOrderByWithRelationInput[]
    cursor?: CheckInRecordWhereUniqueInput
    take?: number
    skip?: number
    distinct?: CheckInRecordScalarFieldEnum | CheckInRecordScalarFieldEnum[]
  }

  /**
   * Session.tickets
   */
  export type Session$ticketsArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Ticket
     */
    select?: TicketSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Ticket
     */
    omit?: TicketOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: TicketInclude<ExtArgs> | null
    where?: TicketWhereInput
    orderBy?: TicketOrderByWithRelationInput | TicketOrderByWithRelationInput[]
    cursor?: TicketWhereUniqueInput
    take?: number
    skip?: number
    distinct?: TicketScalarFieldEnum | TicketScalarFieldEnum[]
  }

  /**
   * Session without action
   */
  export type SessionDefaultArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Session
     */
    select?: SessionSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Session
     */
    omit?: SessionOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: SessionInclude<ExtArgs> | null
  }


  /**
   * Model Ticket
   */

  export type AggregateTicket = {
    _count: TicketCountAggregateOutputType | null
    _min: TicketMinAggregateOutputType | null
    _max: TicketMaxAggregateOutputType | null
  }

  export type TicketMinAggregateOutputType = {
    id: string | null
    type: string | null
    childId: string | null
    sessionId: string | null
  }

  export type TicketMaxAggregateOutputType = {
    id: string | null
    type: string | null
    childId: string | null
    sessionId: string | null
  }

  export type TicketCountAggregateOutputType = {
    id: number
    type: number
    childId: number
    sessionId: number
    _all: number
  }


  export type TicketMinAggregateInputType = {
    id?: true
    type?: true
    childId?: true
    sessionId?: true
  }

  export type TicketMaxAggregateInputType = {
    id?: true
    type?: true
    childId?: true
    sessionId?: true
  }

  export type TicketCountAggregateInputType = {
    id?: true
    type?: true
    childId?: true
    sessionId?: true
    _all?: true
  }

  export type TicketAggregateArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Filter which Ticket to aggregate.
     */
    where?: TicketWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of Tickets to fetch.
     */
    orderBy?: TicketOrderByWithRelationInput | TicketOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the start position
     */
    cursor?: TicketWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` Tickets from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` Tickets.
     */
    skip?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/aggregations Aggregation Docs}
     * 
     * Count returned Tickets
    **/
    _count?: true | TicketCountAggregateInputType
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/aggregations Aggregation Docs}
     * 
     * Select which fields to find the minimum value
    **/
    _min?: TicketMinAggregateInputType
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/aggregations Aggregation Docs}
     * 
     * Select which fields to find the maximum value
    **/
    _max?: TicketMaxAggregateInputType
  }

  export type GetTicketAggregateType<T extends TicketAggregateArgs> = {
        [P in keyof T & keyof AggregateTicket]: P extends '_count' | 'count'
      ? T[P] extends true
        ? number
        : GetScalarType<T[P], AggregateTicket[P]>
      : GetScalarType<T[P], AggregateTicket[P]>
  }




  export type TicketGroupByArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    where?: TicketWhereInput
    orderBy?: TicketOrderByWithAggregationInput | TicketOrderByWithAggregationInput[]
    by: TicketScalarFieldEnum[] | TicketScalarFieldEnum
    having?: TicketScalarWhereWithAggregatesInput
    take?: number
    skip?: number
    _count?: TicketCountAggregateInputType | true
    _min?: TicketMinAggregateInputType
    _max?: TicketMaxAggregateInputType
  }

  export type TicketGroupByOutputType = {
    id: string
    type: string
    childId: string
    sessionId: string | null
    _count: TicketCountAggregateOutputType | null
    _min: TicketMinAggregateOutputType | null
    _max: TicketMaxAggregateOutputType | null
  }

  type GetTicketGroupByPayload<T extends TicketGroupByArgs> = Prisma.PrismaPromise<
    Array<
      PickEnumerable<TicketGroupByOutputType, T['by']> &
        {
          [P in ((keyof T) & (keyof TicketGroupByOutputType))]: P extends '_count'
            ? T[P] extends boolean
              ? number
              : GetScalarType<T[P], TicketGroupByOutputType[P]>
            : GetScalarType<T[P], TicketGroupByOutputType[P]>
        }
      >
    >


  export type TicketSelect<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetSelect<{
    id?: boolean
    type?: boolean
    childId?: boolean
    sessionId?: boolean
    child?: boolean | ChildDefaultArgs<ExtArgs>
    session?: boolean | Ticket$sessionArgs<ExtArgs>
  }, ExtArgs["result"]["ticket"]>

  export type TicketSelectCreateManyAndReturn<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetSelect<{
    id?: boolean
    type?: boolean
    childId?: boolean
    sessionId?: boolean
    child?: boolean | ChildDefaultArgs<ExtArgs>
    session?: boolean | Ticket$sessionArgs<ExtArgs>
  }, ExtArgs["result"]["ticket"]>

  export type TicketSelectUpdateManyAndReturn<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetSelect<{
    id?: boolean
    type?: boolean
    childId?: boolean
    sessionId?: boolean
    child?: boolean | ChildDefaultArgs<ExtArgs>
    session?: boolean | Ticket$sessionArgs<ExtArgs>
  }, ExtArgs["result"]["ticket"]>

  export type TicketSelectScalar = {
    id?: boolean
    type?: boolean
    childId?: boolean
    sessionId?: boolean
  }

  export type TicketOmit<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetOmit<"id" | "type" | "childId" | "sessionId", ExtArgs["result"]["ticket"]>
  export type TicketInclude<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    child?: boolean | ChildDefaultArgs<ExtArgs>
    session?: boolean | Ticket$sessionArgs<ExtArgs>
  }
  export type TicketIncludeCreateManyAndReturn<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    child?: boolean | ChildDefaultArgs<ExtArgs>
    session?: boolean | Ticket$sessionArgs<ExtArgs>
  }
  export type TicketIncludeUpdateManyAndReturn<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    child?: boolean | ChildDefaultArgs<ExtArgs>
    session?: boolean | Ticket$sessionArgs<ExtArgs>
  }

  export type $TicketPayload<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    name: "Ticket"
    objects: {
      child: Prisma.$ChildPayload<ExtArgs>
      session: Prisma.$SessionPayload<ExtArgs> | null
    }
    scalars: $Extensions.GetPayloadResult<{
      id: string
      type: string
      childId: string
      sessionId: string | null
    }, ExtArgs["result"]["ticket"]>
    composites: {}
  }

  type TicketGetPayload<S extends boolean | null | undefined | TicketDefaultArgs> = $Result.GetResult<Prisma.$TicketPayload, S>

  type TicketCountArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> =
    Omit<TicketFindManyArgs, 'select' | 'include' | 'distinct' | 'omit'> & {
      select?: TicketCountAggregateInputType | true
    }

  export interface TicketDelegate<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs, GlobalOmitOptions = {}> {
    [K: symbol]: { types: Prisma.TypeMap<ExtArgs>['model']['Ticket'], meta: { name: 'Ticket' } }
    /**
     * Find zero or one Ticket that matches the filter.
     * @param {TicketFindUniqueArgs} args - Arguments to find a Ticket
     * @example
     * // Get one Ticket
     * const ticket = await prisma.ticket.findUnique({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findUnique<T extends TicketFindUniqueArgs>(args: SelectSubset<T, TicketFindUniqueArgs<ExtArgs>>): Prisma__TicketClient<$Result.GetResult<Prisma.$TicketPayload<ExtArgs>, T, "findUnique", GlobalOmitOptions> | null, null, ExtArgs, GlobalOmitOptions>

    /**
     * Find one Ticket that matches the filter or throw an error with `error.code='P2025'`
     * if no matches were found.
     * @param {TicketFindUniqueOrThrowArgs} args - Arguments to find a Ticket
     * @example
     * // Get one Ticket
     * const ticket = await prisma.ticket.findUniqueOrThrow({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findUniqueOrThrow<T extends TicketFindUniqueOrThrowArgs>(args: SelectSubset<T, TicketFindUniqueOrThrowArgs<ExtArgs>>): Prisma__TicketClient<$Result.GetResult<Prisma.$TicketPayload<ExtArgs>, T, "findUniqueOrThrow", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Find the first Ticket that matches the filter.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {TicketFindFirstArgs} args - Arguments to find a Ticket
     * @example
     * // Get one Ticket
     * const ticket = await prisma.ticket.findFirst({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findFirst<T extends TicketFindFirstArgs>(args?: SelectSubset<T, TicketFindFirstArgs<ExtArgs>>): Prisma__TicketClient<$Result.GetResult<Prisma.$TicketPayload<ExtArgs>, T, "findFirst", GlobalOmitOptions> | null, null, ExtArgs, GlobalOmitOptions>

    /**
     * Find the first Ticket that matches the filter or
     * throw `PrismaKnownClientError` with `P2025` code if no matches were found.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {TicketFindFirstOrThrowArgs} args - Arguments to find a Ticket
     * @example
     * // Get one Ticket
     * const ticket = await prisma.ticket.findFirstOrThrow({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findFirstOrThrow<T extends TicketFindFirstOrThrowArgs>(args?: SelectSubset<T, TicketFindFirstOrThrowArgs<ExtArgs>>): Prisma__TicketClient<$Result.GetResult<Prisma.$TicketPayload<ExtArgs>, T, "findFirstOrThrow", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Find zero or more Tickets that matches the filter.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {TicketFindManyArgs} args - Arguments to filter and select certain fields only.
     * @example
     * // Get all Tickets
     * const tickets = await prisma.ticket.findMany()
     * 
     * // Get first 10 Tickets
     * const tickets = await prisma.ticket.findMany({ take: 10 })
     * 
     * // Only select the `id`
     * const ticketWithIdOnly = await prisma.ticket.findMany({ select: { id: true } })
     * 
     */
    findMany<T extends TicketFindManyArgs>(args?: SelectSubset<T, TicketFindManyArgs<ExtArgs>>): Prisma.PrismaPromise<$Result.GetResult<Prisma.$TicketPayload<ExtArgs>, T, "findMany", GlobalOmitOptions>>

    /**
     * Create a Ticket.
     * @param {TicketCreateArgs} args - Arguments to create a Ticket.
     * @example
     * // Create one Ticket
     * const Ticket = await prisma.ticket.create({
     *   data: {
     *     // ... data to create a Ticket
     *   }
     * })
     * 
     */
    create<T extends TicketCreateArgs>(args: SelectSubset<T, TicketCreateArgs<ExtArgs>>): Prisma__TicketClient<$Result.GetResult<Prisma.$TicketPayload<ExtArgs>, T, "create", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Create many Tickets.
     * @param {TicketCreateManyArgs} args - Arguments to create many Tickets.
     * @example
     * // Create many Tickets
     * const ticket = await prisma.ticket.createMany({
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     *     
     */
    createMany<T extends TicketCreateManyArgs>(args?: SelectSubset<T, TicketCreateManyArgs<ExtArgs>>): Prisma.PrismaPromise<BatchPayload>

    /**
     * Create many Tickets and returns the data saved in the database.
     * @param {TicketCreateManyAndReturnArgs} args - Arguments to create many Tickets.
     * @example
     * // Create many Tickets
     * const ticket = await prisma.ticket.createManyAndReturn({
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * 
     * // Create many Tickets and only return the `id`
     * const ticketWithIdOnly = await prisma.ticket.createManyAndReturn({
     *   select: { id: true },
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * 
     */
    createManyAndReturn<T extends TicketCreateManyAndReturnArgs>(args?: SelectSubset<T, TicketCreateManyAndReturnArgs<ExtArgs>>): Prisma.PrismaPromise<$Result.GetResult<Prisma.$TicketPayload<ExtArgs>, T, "createManyAndReturn", GlobalOmitOptions>>

    /**
     * Delete a Ticket.
     * @param {TicketDeleteArgs} args - Arguments to delete one Ticket.
     * @example
     * // Delete one Ticket
     * const Ticket = await prisma.ticket.delete({
     *   where: {
     *     // ... filter to delete one Ticket
     *   }
     * })
     * 
     */
    delete<T extends TicketDeleteArgs>(args: SelectSubset<T, TicketDeleteArgs<ExtArgs>>): Prisma__TicketClient<$Result.GetResult<Prisma.$TicketPayload<ExtArgs>, T, "delete", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Update one Ticket.
     * @param {TicketUpdateArgs} args - Arguments to update one Ticket.
     * @example
     * // Update one Ticket
     * const ticket = await prisma.ticket.update({
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: {
     *     // ... provide data here
     *   }
     * })
     * 
     */
    update<T extends TicketUpdateArgs>(args: SelectSubset<T, TicketUpdateArgs<ExtArgs>>): Prisma__TicketClient<$Result.GetResult<Prisma.$TicketPayload<ExtArgs>, T, "update", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Delete zero or more Tickets.
     * @param {TicketDeleteManyArgs} args - Arguments to filter Tickets to delete.
     * @example
     * // Delete a few Tickets
     * const { count } = await prisma.ticket.deleteMany({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     * 
     */
    deleteMany<T extends TicketDeleteManyArgs>(args?: SelectSubset<T, TicketDeleteManyArgs<ExtArgs>>): Prisma.PrismaPromise<BatchPayload>

    /**
     * Update zero or more Tickets.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {TicketUpdateManyArgs} args - Arguments to update one or more rows.
     * @example
     * // Update many Tickets
     * const ticket = await prisma.ticket.updateMany({
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: {
     *     // ... provide data here
     *   }
     * })
     * 
     */
    updateMany<T extends TicketUpdateManyArgs>(args: SelectSubset<T, TicketUpdateManyArgs<ExtArgs>>): Prisma.PrismaPromise<BatchPayload>

    /**
     * Update zero or more Tickets and returns the data updated in the database.
     * @param {TicketUpdateManyAndReturnArgs} args - Arguments to update many Tickets.
     * @example
     * // Update many Tickets
     * const ticket = await prisma.ticket.updateManyAndReturn({
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * 
     * // Update zero or more Tickets and only return the `id`
     * const ticketWithIdOnly = await prisma.ticket.updateManyAndReturn({
     *   select: { id: true },
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * 
     */
    updateManyAndReturn<T extends TicketUpdateManyAndReturnArgs>(args: SelectSubset<T, TicketUpdateManyAndReturnArgs<ExtArgs>>): Prisma.PrismaPromise<$Result.GetResult<Prisma.$TicketPayload<ExtArgs>, T, "updateManyAndReturn", GlobalOmitOptions>>

    /**
     * Create or update one Ticket.
     * @param {TicketUpsertArgs} args - Arguments to update or create a Ticket.
     * @example
     * // Update or create a Ticket
     * const ticket = await prisma.ticket.upsert({
     *   create: {
     *     // ... data to create a Ticket
     *   },
     *   update: {
     *     // ... in case it already exists, update
     *   },
     *   where: {
     *     // ... the filter for the Ticket we want to update
     *   }
     * })
     */
    upsert<T extends TicketUpsertArgs>(args: SelectSubset<T, TicketUpsertArgs<ExtArgs>>): Prisma__TicketClient<$Result.GetResult<Prisma.$TicketPayload<ExtArgs>, T, "upsert", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>


    /**
     * Count the number of Tickets.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {TicketCountArgs} args - Arguments to filter Tickets to count.
     * @example
     * // Count the number of Tickets
     * const count = await prisma.ticket.count({
     *   where: {
     *     // ... the filter for the Tickets we want to count
     *   }
     * })
    **/
    count<T extends TicketCountArgs>(
      args?: Subset<T, TicketCountArgs>,
    ): Prisma.PrismaPromise<
      T extends $Utils.Record<'select', any>
        ? T['select'] extends true
          ? number
          : GetScalarType<T['select'], TicketCountAggregateOutputType>
        : number
    >

    /**
     * Allows you to perform aggregations operations on a Ticket.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {TicketAggregateArgs} args - Select which aggregations you would like to apply and on what fields.
     * @example
     * // Ordered by age ascending
     * // Where email contains prisma.io
     * // Limited to the 10 users
     * const aggregations = await prisma.user.aggregate({
     *   _avg: {
     *     age: true,
     *   },
     *   where: {
     *     email: {
     *       contains: "prisma.io",
     *     },
     *   },
     *   orderBy: {
     *     age: "asc",
     *   },
     *   take: 10,
     * })
    **/
    aggregate<T extends TicketAggregateArgs>(args: Subset<T, TicketAggregateArgs>): Prisma.PrismaPromise<GetTicketAggregateType<T>>

    /**
     * Group by Ticket.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {TicketGroupByArgs} args - Group by arguments.
     * @example
     * // Group by city, order by createdAt, get count
     * const result = await prisma.user.groupBy({
     *   by: ['city', 'createdAt'],
     *   orderBy: {
     *     createdAt: true
     *   },
     *   _count: {
     *     _all: true
     *   },
     * })
     * 
    **/
    groupBy<
      T extends TicketGroupByArgs,
      HasSelectOrTake extends Or<
        Extends<'skip', Keys<T>>,
        Extends<'take', Keys<T>>
      >,
      OrderByArg extends True extends HasSelectOrTake
        ? { orderBy: TicketGroupByArgs['orderBy'] }
        : { orderBy?: TicketGroupByArgs['orderBy'] },
      OrderFields extends ExcludeUnderscoreKeys<Keys<MaybeTupleToUnion<T['orderBy']>>>,
      ByFields extends MaybeTupleToUnion<T['by']>,
      ByValid extends Has<ByFields, OrderFields>,
      HavingFields extends GetHavingFields<T['having']>,
      HavingValid extends Has<ByFields, HavingFields>,
      ByEmpty extends T['by'] extends never[] ? True : False,
      InputErrors extends ByEmpty extends True
      ? `Error: "by" must not be empty.`
      : HavingValid extends False
      ? {
          [P in HavingFields]: P extends ByFields
            ? never
            : P extends string
            ? `Error: Field "${P}" used in "having" needs to be provided in "by".`
            : [
                Error,
                'Field ',
                P,
                ` in "having" needs to be provided in "by"`,
              ]
        }[HavingFields]
      : 'take' extends Keys<T>
      ? 'orderBy' extends Keys<T>
        ? ByValid extends True
          ? {}
          : {
              [P in OrderFields]: P extends ByFields
                ? never
                : `Error: Field "${P}" in "orderBy" needs to be provided in "by"`
            }[OrderFields]
        : 'Error: If you provide "take", you also need to provide "orderBy"'
      : 'skip' extends Keys<T>
      ? 'orderBy' extends Keys<T>
        ? ByValid extends True
          ? {}
          : {
              [P in OrderFields]: P extends ByFields
                ? never
                : `Error: Field "${P}" in "orderBy" needs to be provided in "by"`
            }[OrderFields]
        : 'Error: If you provide "skip", you also need to provide "orderBy"'
      : ByValid extends True
      ? {}
      : {
          [P in OrderFields]: P extends ByFields
            ? never
            : `Error: Field "${P}" in "orderBy" needs to be provided in "by"`
        }[OrderFields]
    >(args: SubsetIntersection<T, TicketGroupByArgs, OrderByArg> & InputErrors): {} extends InputErrors ? GetTicketGroupByPayload<T> : Prisma.PrismaPromise<InputErrors>
  /**
   * Fields of the Ticket model
   */
  readonly fields: TicketFieldRefs;
  }

  /**
   * The delegate class that acts as a "Promise-like" for Ticket.
   * Why is this prefixed with `Prisma__`?
   * Because we want to prevent naming conflicts as mentioned in
   * https://github.com/prisma/prisma-client-js/issues/707
   */
  export interface Prisma__TicketClient<T, Null = never, ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs, GlobalOmitOptions = {}> extends Prisma.PrismaPromise<T> {
    readonly [Symbol.toStringTag]: "PrismaPromise"
    child<T extends ChildDefaultArgs<ExtArgs> = {}>(args?: Subset<T, ChildDefaultArgs<ExtArgs>>): Prisma__ChildClient<$Result.GetResult<Prisma.$ChildPayload<ExtArgs>, T, "findUniqueOrThrow", GlobalOmitOptions> | Null, Null, ExtArgs, GlobalOmitOptions>
    session<T extends Ticket$sessionArgs<ExtArgs> = {}>(args?: Subset<T, Ticket$sessionArgs<ExtArgs>>): Prisma__SessionClient<$Result.GetResult<Prisma.$SessionPayload<ExtArgs>, T, "findUniqueOrThrow", GlobalOmitOptions> | null, null, ExtArgs, GlobalOmitOptions>
    /**
     * Attaches callbacks for the resolution and/or rejection of the Promise.
     * @param onfulfilled The callback to execute when the Promise is resolved.
     * @param onrejected The callback to execute when the Promise is rejected.
     * @returns A Promise for the completion of which ever callback is executed.
     */
    then<TResult1 = T, TResult2 = never>(onfulfilled?: ((value: T) => TResult1 | PromiseLike<TResult1>) | undefined | null, onrejected?: ((reason: any) => TResult2 | PromiseLike<TResult2>) | undefined | null): $Utils.JsPromise<TResult1 | TResult2>
    /**
     * Attaches a callback for only the rejection of the Promise.
     * @param onrejected The callback to execute when the Promise is rejected.
     * @returns A Promise for the completion of the callback.
     */
    catch<TResult = never>(onrejected?: ((reason: any) => TResult | PromiseLike<TResult>) | undefined | null): $Utils.JsPromise<T | TResult>
    /**
     * Attaches a callback that is invoked when the Promise is settled (fulfilled or rejected). The
     * resolved value cannot be modified from the callback.
     * @param onfinally The callback to execute when the Promise is settled (fulfilled or rejected).
     * @returns A Promise for the completion of the callback.
     */
    finally(onfinally?: (() => void) | undefined | null): $Utils.JsPromise<T>
  }




  /**
   * Fields of the Ticket model
   */
  interface TicketFieldRefs {
    readonly id: FieldRef<"Ticket", 'String'>
    readonly type: FieldRef<"Ticket", 'String'>
    readonly childId: FieldRef<"Ticket", 'String'>
    readonly sessionId: FieldRef<"Ticket", 'String'>
  }
    

  // Custom InputTypes
  /**
   * Ticket findUnique
   */
  export type TicketFindUniqueArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Ticket
     */
    select?: TicketSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Ticket
     */
    omit?: TicketOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: TicketInclude<ExtArgs> | null
    /**
     * Filter, which Ticket to fetch.
     */
    where: TicketWhereUniqueInput
  }

  /**
   * Ticket findUniqueOrThrow
   */
  export type TicketFindUniqueOrThrowArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Ticket
     */
    select?: TicketSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Ticket
     */
    omit?: TicketOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: TicketInclude<ExtArgs> | null
    /**
     * Filter, which Ticket to fetch.
     */
    where: TicketWhereUniqueInput
  }

  /**
   * Ticket findFirst
   */
  export type TicketFindFirstArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Ticket
     */
    select?: TicketSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Ticket
     */
    omit?: TicketOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: TicketInclude<ExtArgs> | null
    /**
     * Filter, which Ticket to fetch.
     */
    where?: TicketWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of Tickets to fetch.
     */
    orderBy?: TicketOrderByWithRelationInput | TicketOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the position for searching for Tickets.
     */
    cursor?: TicketWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` Tickets from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` Tickets.
     */
    skip?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/distinct Distinct Docs}
     * 
     * Filter by unique combinations of Tickets.
     */
    distinct?: TicketScalarFieldEnum | TicketScalarFieldEnum[]
  }

  /**
   * Ticket findFirstOrThrow
   */
  export type TicketFindFirstOrThrowArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Ticket
     */
    select?: TicketSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Ticket
     */
    omit?: TicketOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: TicketInclude<ExtArgs> | null
    /**
     * Filter, which Ticket to fetch.
     */
    where?: TicketWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of Tickets to fetch.
     */
    orderBy?: TicketOrderByWithRelationInput | TicketOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the position for searching for Tickets.
     */
    cursor?: TicketWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` Tickets from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` Tickets.
     */
    skip?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/distinct Distinct Docs}
     * 
     * Filter by unique combinations of Tickets.
     */
    distinct?: TicketScalarFieldEnum | TicketScalarFieldEnum[]
  }

  /**
   * Ticket findMany
   */
  export type TicketFindManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Ticket
     */
    select?: TicketSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Ticket
     */
    omit?: TicketOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: TicketInclude<ExtArgs> | null
    /**
     * Filter, which Tickets to fetch.
     */
    where?: TicketWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of Tickets to fetch.
     */
    orderBy?: TicketOrderByWithRelationInput | TicketOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the position for listing Tickets.
     */
    cursor?: TicketWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` Tickets from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` Tickets.
     */
    skip?: number
    distinct?: TicketScalarFieldEnum | TicketScalarFieldEnum[]
  }

  /**
   * Ticket create
   */
  export type TicketCreateArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Ticket
     */
    select?: TicketSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Ticket
     */
    omit?: TicketOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: TicketInclude<ExtArgs> | null
    /**
     * The data needed to create a Ticket.
     */
    data: XOR<TicketCreateInput, TicketUncheckedCreateInput>
  }

  /**
   * Ticket createMany
   */
  export type TicketCreateManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * The data used to create many Tickets.
     */
    data: TicketCreateManyInput | TicketCreateManyInput[]
    skipDuplicates?: boolean
  }

  /**
   * Ticket createManyAndReturn
   */
  export type TicketCreateManyAndReturnArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Ticket
     */
    select?: TicketSelectCreateManyAndReturn<ExtArgs> | null
    /**
     * Omit specific fields from the Ticket
     */
    omit?: TicketOmit<ExtArgs> | null
    /**
     * The data used to create many Tickets.
     */
    data: TicketCreateManyInput | TicketCreateManyInput[]
    skipDuplicates?: boolean
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: TicketIncludeCreateManyAndReturn<ExtArgs> | null
  }

  /**
   * Ticket update
   */
  export type TicketUpdateArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Ticket
     */
    select?: TicketSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Ticket
     */
    omit?: TicketOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: TicketInclude<ExtArgs> | null
    /**
     * The data needed to update a Ticket.
     */
    data: XOR<TicketUpdateInput, TicketUncheckedUpdateInput>
    /**
     * Choose, which Ticket to update.
     */
    where: TicketWhereUniqueInput
  }

  /**
   * Ticket updateMany
   */
  export type TicketUpdateManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * The data used to update Tickets.
     */
    data: XOR<TicketUpdateManyMutationInput, TicketUncheckedUpdateManyInput>
    /**
     * Filter which Tickets to update
     */
    where?: TicketWhereInput
    /**
     * Limit how many Tickets to update.
     */
    limit?: number
  }

  /**
   * Ticket updateManyAndReturn
   */
  export type TicketUpdateManyAndReturnArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Ticket
     */
    select?: TicketSelectUpdateManyAndReturn<ExtArgs> | null
    /**
     * Omit specific fields from the Ticket
     */
    omit?: TicketOmit<ExtArgs> | null
    /**
     * The data used to update Tickets.
     */
    data: XOR<TicketUpdateManyMutationInput, TicketUncheckedUpdateManyInput>
    /**
     * Filter which Tickets to update
     */
    where?: TicketWhereInput
    /**
     * Limit how many Tickets to update.
     */
    limit?: number
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: TicketIncludeUpdateManyAndReturn<ExtArgs> | null
  }

  /**
   * Ticket upsert
   */
  export type TicketUpsertArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Ticket
     */
    select?: TicketSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Ticket
     */
    omit?: TicketOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: TicketInclude<ExtArgs> | null
    /**
     * The filter to search for the Ticket to update in case it exists.
     */
    where: TicketWhereUniqueInput
    /**
     * In case the Ticket found by the `where` argument doesn't exist, create a new Ticket with this data.
     */
    create: XOR<TicketCreateInput, TicketUncheckedCreateInput>
    /**
     * In case the Ticket was found with the provided `where` argument, update it with this data.
     */
    update: XOR<TicketUpdateInput, TicketUncheckedUpdateInput>
  }

  /**
   * Ticket delete
   */
  export type TicketDeleteArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Ticket
     */
    select?: TicketSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Ticket
     */
    omit?: TicketOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: TicketInclude<ExtArgs> | null
    /**
     * Filter which Ticket to delete.
     */
    where: TicketWhereUniqueInput
  }

  /**
   * Ticket deleteMany
   */
  export type TicketDeleteManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Filter which Tickets to delete
     */
    where?: TicketWhereInput
    /**
     * Limit how many Tickets to delete.
     */
    limit?: number
  }

  /**
   * Ticket.session
   */
  export type Ticket$sessionArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Session
     */
    select?: SessionSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Session
     */
    omit?: SessionOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: SessionInclude<ExtArgs> | null
    where?: SessionWhereInput
  }

  /**
   * Ticket without action
   */
  export type TicketDefaultArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the Ticket
     */
    select?: TicketSelect<ExtArgs> | null
    /**
     * Omit specific fields from the Ticket
     */
    omit?: TicketOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: TicketInclude<ExtArgs> | null
  }


  /**
   * Model CheckInRecord
   */

  export type AggregateCheckInRecord = {
    _count: CheckInRecordCountAggregateOutputType | null
    _min: CheckInRecordMinAggregateOutputType | null
    _max: CheckInRecordMaxAggregateOutputType | null
  }

  export type CheckInRecordMinAggregateOutputType = {
    id: string | null
    checkInTime: Date | null
    checkOutTime: Date | null
    pickedUpBy: string | null
    childId: string | null
    sessionId: string | null
    checkInStaffId: string | null
    checkOutStaffId: string | null
  }

  export type CheckInRecordMaxAggregateOutputType = {
    id: string | null
    checkInTime: Date | null
    checkOutTime: Date | null
    pickedUpBy: string | null
    childId: string | null
    sessionId: string | null
    checkInStaffId: string | null
    checkOutStaffId: string | null
  }

  export type CheckInRecordCountAggregateOutputType = {
    id: number
    checkInTime: number
    checkOutTime: number
    pickedUpBy: number
    childId: number
    sessionId: number
    checkInStaffId: number
    checkOutStaffId: number
    _all: number
  }


  export type CheckInRecordMinAggregateInputType = {
    id?: true
    checkInTime?: true
    checkOutTime?: true
    pickedUpBy?: true
    childId?: true
    sessionId?: true
    checkInStaffId?: true
    checkOutStaffId?: true
  }

  export type CheckInRecordMaxAggregateInputType = {
    id?: true
    checkInTime?: true
    checkOutTime?: true
    pickedUpBy?: true
    childId?: true
    sessionId?: true
    checkInStaffId?: true
    checkOutStaffId?: true
  }

  export type CheckInRecordCountAggregateInputType = {
    id?: true
    checkInTime?: true
    checkOutTime?: true
    pickedUpBy?: true
    childId?: true
    sessionId?: true
    checkInStaffId?: true
    checkOutStaffId?: true
    _all?: true
  }

  export type CheckInRecordAggregateArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Filter which CheckInRecord to aggregate.
     */
    where?: CheckInRecordWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of CheckInRecords to fetch.
     */
    orderBy?: CheckInRecordOrderByWithRelationInput | CheckInRecordOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the start position
     */
    cursor?: CheckInRecordWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` CheckInRecords from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` CheckInRecords.
     */
    skip?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/aggregations Aggregation Docs}
     * 
     * Count returned CheckInRecords
    **/
    _count?: true | CheckInRecordCountAggregateInputType
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/aggregations Aggregation Docs}
     * 
     * Select which fields to find the minimum value
    **/
    _min?: CheckInRecordMinAggregateInputType
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/aggregations Aggregation Docs}
     * 
     * Select which fields to find the maximum value
    **/
    _max?: CheckInRecordMaxAggregateInputType
  }

  export type GetCheckInRecordAggregateType<T extends CheckInRecordAggregateArgs> = {
        [P in keyof T & keyof AggregateCheckInRecord]: P extends '_count' | 'count'
      ? T[P] extends true
        ? number
        : GetScalarType<T[P], AggregateCheckInRecord[P]>
      : GetScalarType<T[P], AggregateCheckInRecord[P]>
  }




  export type CheckInRecordGroupByArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    where?: CheckInRecordWhereInput
    orderBy?: CheckInRecordOrderByWithAggregationInput | CheckInRecordOrderByWithAggregationInput[]
    by: CheckInRecordScalarFieldEnum[] | CheckInRecordScalarFieldEnum
    having?: CheckInRecordScalarWhereWithAggregatesInput
    take?: number
    skip?: number
    _count?: CheckInRecordCountAggregateInputType | true
    _min?: CheckInRecordMinAggregateInputType
    _max?: CheckInRecordMaxAggregateInputType
  }

  export type CheckInRecordGroupByOutputType = {
    id: string
    checkInTime: Date
    checkOutTime: Date | null
    pickedUpBy: string | null
    childId: string
    sessionId: string
    checkInStaffId: string
    checkOutStaffId: string | null
    _count: CheckInRecordCountAggregateOutputType | null
    _min: CheckInRecordMinAggregateOutputType | null
    _max: CheckInRecordMaxAggregateOutputType | null
  }

  type GetCheckInRecordGroupByPayload<T extends CheckInRecordGroupByArgs> = Prisma.PrismaPromise<
    Array<
      PickEnumerable<CheckInRecordGroupByOutputType, T['by']> &
        {
          [P in ((keyof T) & (keyof CheckInRecordGroupByOutputType))]: P extends '_count'
            ? T[P] extends boolean
              ? number
              : GetScalarType<T[P], CheckInRecordGroupByOutputType[P]>
            : GetScalarType<T[P], CheckInRecordGroupByOutputType[P]>
        }
      >
    >


  export type CheckInRecordSelect<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetSelect<{
    id?: boolean
    checkInTime?: boolean
    checkOutTime?: boolean
    pickedUpBy?: boolean
    childId?: boolean
    sessionId?: boolean
    checkInStaffId?: boolean
    checkOutStaffId?: boolean
    child?: boolean | ChildDefaultArgs<ExtArgs>
    session?: boolean | SessionDefaultArgs<ExtArgs>
    checkInStaff?: boolean | AdminUserDefaultArgs<ExtArgs>
    checkOutStaff?: boolean | CheckInRecord$checkOutStaffArgs<ExtArgs>
  }, ExtArgs["result"]["checkInRecord"]>

  export type CheckInRecordSelectCreateManyAndReturn<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetSelect<{
    id?: boolean
    checkInTime?: boolean
    checkOutTime?: boolean
    pickedUpBy?: boolean
    childId?: boolean
    sessionId?: boolean
    checkInStaffId?: boolean
    checkOutStaffId?: boolean
    child?: boolean | ChildDefaultArgs<ExtArgs>
    session?: boolean | SessionDefaultArgs<ExtArgs>
    checkInStaff?: boolean | AdminUserDefaultArgs<ExtArgs>
    checkOutStaff?: boolean | CheckInRecord$checkOutStaffArgs<ExtArgs>
  }, ExtArgs["result"]["checkInRecord"]>

  export type CheckInRecordSelectUpdateManyAndReturn<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetSelect<{
    id?: boolean
    checkInTime?: boolean
    checkOutTime?: boolean
    pickedUpBy?: boolean
    childId?: boolean
    sessionId?: boolean
    checkInStaffId?: boolean
    checkOutStaffId?: boolean
    child?: boolean | ChildDefaultArgs<ExtArgs>
    session?: boolean | SessionDefaultArgs<ExtArgs>
    checkInStaff?: boolean | AdminUserDefaultArgs<ExtArgs>
    checkOutStaff?: boolean | CheckInRecord$checkOutStaffArgs<ExtArgs>
  }, ExtArgs["result"]["checkInRecord"]>

  export type CheckInRecordSelectScalar = {
    id?: boolean
    checkInTime?: boolean
    checkOutTime?: boolean
    pickedUpBy?: boolean
    childId?: boolean
    sessionId?: boolean
    checkInStaffId?: boolean
    checkOutStaffId?: boolean
  }

  export type CheckInRecordOmit<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetOmit<"id" | "checkInTime" | "checkOutTime" | "pickedUpBy" | "childId" | "sessionId" | "checkInStaffId" | "checkOutStaffId", ExtArgs["result"]["checkInRecord"]>
  export type CheckInRecordInclude<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    child?: boolean | ChildDefaultArgs<ExtArgs>
    session?: boolean | SessionDefaultArgs<ExtArgs>
    checkInStaff?: boolean | AdminUserDefaultArgs<ExtArgs>
    checkOutStaff?: boolean | CheckInRecord$checkOutStaffArgs<ExtArgs>
  }
  export type CheckInRecordIncludeCreateManyAndReturn<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    child?: boolean | ChildDefaultArgs<ExtArgs>
    session?: boolean | SessionDefaultArgs<ExtArgs>
    checkInStaff?: boolean | AdminUserDefaultArgs<ExtArgs>
    checkOutStaff?: boolean | CheckInRecord$checkOutStaffArgs<ExtArgs>
  }
  export type CheckInRecordIncludeUpdateManyAndReturn<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    child?: boolean | ChildDefaultArgs<ExtArgs>
    session?: boolean | SessionDefaultArgs<ExtArgs>
    checkInStaff?: boolean | AdminUserDefaultArgs<ExtArgs>
    checkOutStaff?: boolean | CheckInRecord$checkOutStaffArgs<ExtArgs>
  }

  export type $CheckInRecordPayload<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    name: "CheckInRecord"
    objects: {
      child: Prisma.$ChildPayload<ExtArgs>
      session: Prisma.$SessionPayload<ExtArgs>
      checkInStaff: Prisma.$AdminUserPayload<ExtArgs>
      checkOutStaff: Prisma.$AdminUserPayload<ExtArgs> | null
    }
    scalars: $Extensions.GetPayloadResult<{
      id: string
      checkInTime: Date
      checkOutTime: Date | null
      pickedUpBy: string | null
      childId: string
      sessionId: string
      checkInStaffId: string
      checkOutStaffId: string | null
    }, ExtArgs["result"]["checkInRecord"]>
    composites: {}
  }

  type CheckInRecordGetPayload<S extends boolean | null | undefined | CheckInRecordDefaultArgs> = $Result.GetResult<Prisma.$CheckInRecordPayload, S>

  type CheckInRecordCountArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> =
    Omit<CheckInRecordFindManyArgs, 'select' | 'include' | 'distinct' | 'omit'> & {
      select?: CheckInRecordCountAggregateInputType | true
    }

  export interface CheckInRecordDelegate<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs, GlobalOmitOptions = {}> {
    [K: symbol]: { types: Prisma.TypeMap<ExtArgs>['model']['CheckInRecord'], meta: { name: 'CheckInRecord' } }
    /**
     * Find zero or one CheckInRecord that matches the filter.
     * @param {CheckInRecordFindUniqueArgs} args - Arguments to find a CheckInRecord
     * @example
     * // Get one CheckInRecord
     * const checkInRecord = await prisma.checkInRecord.findUnique({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findUnique<T extends CheckInRecordFindUniqueArgs>(args: SelectSubset<T, CheckInRecordFindUniqueArgs<ExtArgs>>): Prisma__CheckInRecordClient<$Result.GetResult<Prisma.$CheckInRecordPayload<ExtArgs>, T, "findUnique", GlobalOmitOptions> | null, null, ExtArgs, GlobalOmitOptions>

    /**
     * Find one CheckInRecord that matches the filter or throw an error with `error.code='P2025'`
     * if no matches were found.
     * @param {CheckInRecordFindUniqueOrThrowArgs} args - Arguments to find a CheckInRecord
     * @example
     * // Get one CheckInRecord
     * const checkInRecord = await prisma.checkInRecord.findUniqueOrThrow({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findUniqueOrThrow<T extends CheckInRecordFindUniqueOrThrowArgs>(args: SelectSubset<T, CheckInRecordFindUniqueOrThrowArgs<ExtArgs>>): Prisma__CheckInRecordClient<$Result.GetResult<Prisma.$CheckInRecordPayload<ExtArgs>, T, "findUniqueOrThrow", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Find the first CheckInRecord that matches the filter.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {CheckInRecordFindFirstArgs} args - Arguments to find a CheckInRecord
     * @example
     * // Get one CheckInRecord
     * const checkInRecord = await prisma.checkInRecord.findFirst({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findFirst<T extends CheckInRecordFindFirstArgs>(args?: SelectSubset<T, CheckInRecordFindFirstArgs<ExtArgs>>): Prisma__CheckInRecordClient<$Result.GetResult<Prisma.$CheckInRecordPayload<ExtArgs>, T, "findFirst", GlobalOmitOptions> | null, null, ExtArgs, GlobalOmitOptions>

    /**
     * Find the first CheckInRecord that matches the filter or
     * throw `PrismaKnownClientError` with `P2025` code if no matches were found.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {CheckInRecordFindFirstOrThrowArgs} args - Arguments to find a CheckInRecord
     * @example
     * // Get one CheckInRecord
     * const checkInRecord = await prisma.checkInRecord.findFirstOrThrow({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findFirstOrThrow<T extends CheckInRecordFindFirstOrThrowArgs>(args?: SelectSubset<T, CheckInRecordFindFirstOrThrowArgs<ExtArgs>>): Prisma__CheckInRecordClient<$Result.GetResult<Prisma.$CheckInRecordPayload<ExtArgs>, T, "findFirstOrThrow", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Find zero or more CheckInRecords that matches the filter.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {CheckInRecordFindManyArgs} args - Arguments to filter and select certain fields only.
     * @example
     * // Get all CheckInRecords
     * const checkInRecords = await prisma.checkInRecord.findMany()
     * 
     * // Get first 10 CheckInRecords
     * const checkInRecords = await prisma.checkInRecord.findMany({ take: 10 })
     * 
     * // Only select the `id`
     * const checkInRecordWithIdOnly = await prisma.checkInRecord.findMany({ select: { id: true } })
     * 
     */
    findMany<T extends CheckInRecordFindManyArgs>(args?: SelectSubset<T, CheckInRecordFindManyArgs<ExtArgs>>): Prisma.PrismaPromise<$Result.GetResult<Prisma.$CheckInRecordPayload<ExtArgs>, T, "findMany", GlobalOmitOptions>>

    /**
     * Create a CheckInRecord.
     * @param {CheckInRecordCreateArgs} args - Arguments to create a CheckInRecord.
     * @example
     * // Create one CheckInRecord
     * const CheckInRecord = await prisma.checkInRecord.create({
     *   data: {
     *     // ... data to create a CheckInRecord
     *   }
     * })
     * 
     */
    create<T extends CheckInRecordCreateArgs>(args: SelectSubset<T, CheckInRecordCreateArgs<ExtArgs>>): Prisma__CheckInRecordClient<$Result.GetResult<Prisma.$CheckInRecordPayload<ExtArgs>, T, "create", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Create many CheckInRecords.
     * @param {CheckInRecordCreateManyArgs} args - Arguments to create many CheckInRecords.
     * @example
     * // Create many CheckInRecords
     * const checkInRecord = await prisma.checkInRecord.createMany({
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     *     
     */
    createMany<T extends CheckInRecordCreateManyArgs>(args?: SelectSubset<T, CheckInRecordCreateManyArgs<ExtArgs>>): Prisma.PrismaPromise<BatchPayload>

    /**
     * Create many CheckInRecords and returns the data saved in the database.
     * @param {CheckInRecordCreateManyAndReturnArgs} args - Arguments to create many CheckInRecords.
     * @example
     * // Create many CheckInRecords
     * const checkInRecord = await prisma.checkInRecord.createManyAndReturn({
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * 
     * // Create many CheckInRecords and only return the `id`
     * const checkInRecordWithIdOnly = await prisma.checkInRecord.createManyAndReturn({
     *   select: { id: true },
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * 
     */
    createManyAndReturn<T extends CheckInRecordCreateManyAndReturnArgs>(args?: SelectSubset<T, CheckInRecordCreateManyAndReturnArgs<ExtArgs>>): Prisma.PrismaPromise<$Result.GetResult<Prisma.$CheckInRecordPayload<ExtArgs>, T, "createManyAndReturn", GlobalOmitOptions>>

    /**
     * Delete a CheckInRecord.
     * @param {CheckInRecordDeleteArgs} args - Arguments to delete one CheckInRecord.
     * @example
     * // Delete one CheckInRecord
     * const CheckInRecord = await prisma.checkInRecord.delete({
     *   where: {
     *     // ... filter to delete one CheckInRecord
     *   }
     * })
     * 
     */
    delete<T extends CheckInRecordDeleteArgs>(args: SelectSubset<T, CheckInRecordDeleteArgs<ExtArgs>>): Prisma__CheckInRecordClient<$Result.GetResult<Prisma.$CheckInRecordPayload<ExtArgs>, T, "delete", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Update one CheckInRecord.
     * @param {CheckInRecordUpdateArgs} args - Arguments to update one CheckInRecord.
     * @example
     * // Update one CheckInRecord
     * const checkInRecord = await prisma.checkInRecord.update({
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: {
     *     // ... provide data here
     *   }
     * })
     * 
     */
    update<T extends CheckInRecordUpdateArgs>(args: SelectSubset<T, CheckInRecordUpdateArgs<ExtArgs>>): Prisma__CheckInRecordClient<$Result.GetResult<Prisma.$CheckInRecordPayload<ExtArgs>, T, "update", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Delete zero or more CheckInRecords.
     * @param {CheckInRecordDeleteManyArgs} args - Arguments to filter CheckInRecords to delete.
     * @example
     * // Delete a few CheckInRecords
     * const { count } = await prisma.checkInRecord.deleteMany({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     * 
     */
    deleteMany<T extends CheckInRecordDeleteManyArgs>(args?: SelectSubset<T, CheckInRecordDeleteManyArgs<ExtArgs>>): Prisma.PrismaPromise<BatchPayload>

    /**
     * Update zero or more CheckInRecords.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {CheckInRecordUpdateManyArgs} args - Arguments to update one or more rows.
     * @example
     * // Update many CheckInRecords
     * const checkInRecord = await prisma.checkInRecord.updateMany({
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: {
     *     // ... provide data here
     *   }
     * })
     * 
     */
    updateMany<T extends CheckInRecordUpdateManyArgs>(args: SelectSubset<T, CheckInRecordUpdateManyArgs<ExtArgs>>): Prisma.PrismaPromise<BatchPayload>

    /**
     * Update zero or more CheckInRecords and returns the data updated in the database.
     * @param {CheckInRecordUpdateManyAndReturnArgs} args - Arguments to update many CheckInRecords.
     * @example
     * // Update many CheckInRecords
     * const checkInRecord = await prisma.checkInRecord.updateManyAndReturn({
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * 
     * // Update zero or more CheckInRecords and only return the `id`
     * const checkInRecordWithIdOnly = await prisma.checkInRecord.updateManyAndReturn({
     *   select: { id: true },
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * 
     */
    updateManyAndReturn<T extends CheckInRecordUpdateManyAndReturnArgs>(args: SelectSubset<T, CheckInRecordUpdateManyAndReturnArgs<ExtArgs>>): Prisma.PrismaPromise<$Result.GetResult<Prisma.$CheckInRecordPayload<ExtArgs>, T, "updateManyAndReturn", GlobalOmitOptions>>

    /**
     * Create or update one CheckInRecord.
     * @param {CheckInRecordUpsertArgs} args - Arguments to update or create a CheckInRecord.
     * @example
     * // Update or create a CheckInRecord
     * const checkInRecord = await prisma.checkInRecord.upsert({
     *   create: {
     *     // ... data to create a CheckInRecord
     *   },
     *   update: {
     *     // ... in case it already exists, update
     *   },
     *   where: {
     *     // ... the filter for the CheckInRecord we want to update
     *   }
     * })
     */
    upsert<T extends CheckInRecordUpsertArgs>(args: SelectSubset<T, CheckInRecordUpsertArgs<ExtArgs>>): Prisma__CheckInRecordClient<$Result.GetResult<Prisma.$CheckInRecordPayload<ExtArgs>, T, "upsert", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>


    /**
     * Count the number of CheckInRecords.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {CheckInRecordCountArgs} args - Arguments to filter CheckInRecords to count.
     * @example
     * // Count the number of CheckInRecords
     * const count = await prisma.checkInRecord.count({
     *   where: {
     *     // ... the filter for the CheckInRecords we want to count
     *   }
     * })
    **/
    count<T extends CheckInRecordCountArgs>(
      args?: Subset<T, CheckInRecordCountArgs>,
    ): Prisma.PrismaPromise<
      T extends $Utils.Record<'select', any>
        ? T['select'] extends true
          ? number
          : GetScalarType<T['select'], CheckInRecordCountAggregateOutputType>
        : number
    >

    /**
     * Allows you to perform aggregations operations on a CheckInRecord.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {CheckInRecordAggregateArgs} args - Select which aggregations you would like to apply and on what fields.
     * @example
     * // Ordered by age ascending
     * // Where email contains prisma.io
     * // Limited to the 10 users
     * const aggregations = await prisma.user.aggregate({
     *   _avg: {
     *     age: true,
     *   },
     *   where: {
     *     email: {
     *       contains: "prisma.io",
     *     },
     *   },
     *   orderBy: {
     *     age: "asc",
     *   },
     *   take: 10,
     * })
    **/
    aggregate<T extends CheckInRecordAggregateArgs>(args: Subset<T, CheckInRecordAggregateArgs>): Prisma.PrismaPromise<GetCheckInRecordAggregateType<T>>

    /**
     * Group by CheckInRecord.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {CheckInRecordGroupByArgs} args - Group by arguments.
     * @example
     * // Group by city, order by createdAt, get count
     * const result = await prisma.user.groupBy({
     *   by: ['city', 'createdAt'],
     *   orderBy: {
     *     createdAt: true
     *   },
     *   _count: {
     *     _all: true
     *   },
     * })
     * 
    **/
    groupBy<
      T extends CheckInRecordGroupByArgs,
      HasSelectOrTake extends Or<
        Extends<'skip', Keys<T>>,
        Extends<'take', Keys<T>>
      >,
      OrderByArg extends True extends HasSelectOrTake
        ? { orderBy: CheckInRecordGroupByArgs['orderBy'] }
        : { orderBy?: CheckInRecordGroupByArgs['orderBy'] },
      OrderFields extends ExcludeUnderscoreKeys<Keys<MaybeTupleToUnion<T['orderBy']>>>,
      ByFields extends MaybeTupleToUnion<T['by']>,
      ByValid extends Has<ByFields, OrderFields>,
      HavingFields extends GetHavingFields<T['having']>,
      HavingValid extends Has<ByFields, HavingFields>,
      ByEmpty extends T['by'] extends never[] ? True : False,
      InputErrors extends ByEmpty extends True
      ? `Error: "by" must not be empty.`
      : HavingValid extends False
      ? {
          [P in HavingFields]: P extends ByFields
            ? never
            : P extends string
            ? `Error: Field "${P}" used in "having" needs to be provided in "by".`
            : [
                Error,
                'Field ',
                P,
                ` in "having" needs to be provided in "by"`,
              ]
        }[HavingFields]
      : 'take' extends Keys<T>
      ? 'orderBy' extends Keys<T>
        ? ByValid extends True
          ? {}
          : {
              [P in OrderFields]: P extends ByFields
                ? never
                : `Error: Field "${P}" in "orderBy" needs to be provided in "by"`
            }[OrderFields]
        : 'Error: If you provide "take", you also need to provide "orderBy"'
      : 'skip' extends Keys<T>
      ? 'orderBy' extends Keys<T>
        ? ByValid extends True
          ? {}
          : {
              [P in OrderFields]: P extends ByFields
                ? never
                : `Error: Field "${P}" in "orderBy" needs to be provided in "by"`
            }[OrderFields]
        : 'Error: If you provide "skip", you also need to provide "orderBy"'
      : ByValid extends True
      ? {}
      : {
          [P in OrderFields]: P extends ByFields
            ? never
            : `Error: Field "${P}" in "orderBy" needs to be provided in "by"`
        }[OrderFields]
    >(args: SubsetIntersection<T, CheckInRecordGroupByArgs, OrderByArg> & InputErrors): {} extends InputErrors ? GetCheckInRecordGroupByPayload<T> : Prisma.PrismaPromise<InputErrors>
  /**
   * Fields of the CheckInRecord model
   */
  readonly fields: CheckInRecordFieldRefs;
  }

  /**
   * The delegate class that acts as a "Promise-like" for CheckInRecord.
   * Why is this prefixed with `Prisma__`?
   * Because we want to prevent naming conflicts as mentioned in
   * https://github.com/prisma/prisma-client-js/issues/707
   */
  export interface Prisma__CheckInRecordClient<T, Null = never, ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs, GlobalOmitOptions = {}> extends Prisma.PrismaPromise<T> {
    readonly [Symbol.toStringTag]: "PrismaPromise"
    child<T extends ChildDefaultArgs<ExtArgs> = {}>(args?: Subset<T, ChildDefaultArgs<ExtArgs>>): Prisma__ChildClient<$Result.GetResult<Prisma.$ChildPayload<ExtArgs>, T, "findUniqueOrThrow", GlobalOmitOptions> | Null, Null, ExtArgs, GlobalOmitOptions>
    session<T extends SessionDefaultArgs<ExtArgs> = {}>(args?: Subset<T, SessionDefaultArgs<ExtArgs>>): Prisma__SessionClient<$Result.GetResult<Prisma.$SessionPayload<ExtArgs>, T, "findUniqueOrThrow", GlobalOmitOptions> | Null, Null, ExtArgs, GlobalOmitOptions>
    checkInStaff<T extends AdminUserDefaultArgs<ExtArgs> = {}>(args?: Subset<T, AdminUserDefaultArgs<ExtArgs>>): Prisma__AdminUserClient<$Result.GetResult<Prisma.$AdminUserPayload<ExtArgs>, T, "findUniqueOrThrow", GlobalOmitOptions> | Null, Null, ExtArgs, GlobalOmitOptions>
    checkOutStaff<T extends CheckInRecord$checkOutStaffArgs<ExtArgs> = {}>(args?: Subset<T, CheckInRecord$checkOutStaffArgs<ExtArgs>>): Prisma__AdminUserClient<$Result.GetResult<Prisma.$AdminUserPayload<ExtArgs>, T, "findUniqueOrThrow", GlobalOmitOptions> | null, null, ExtArgs, GlobalOmitOptions>
    /**
     * Attaches callbacks for the resolution and/or rejection of the Promise.
     * @param onfulfilled The callback to execute when the Promise is resolved.
     * @param onrejected The callback to execute when the Promise is rejected.
     * @returns A Promise for the completion of which ever callback is executed.
     */
    then<TResult1 = T, TResult2 = never>(onfulfilled?: ((value: T) => TResult1 | PromiseLike<TResult1>) | undefined | null, onrejected?: ((reason: any) => TResult2 | PromiseLike<TResult2>) | undefined | null): $Utils.JsPromise<TResult1 | TResult2>
    /**
     * Attaches a callback for only the rejection of the Promise.
     * @param onrejected The callback to execute when the Promise is rejected.
     * @returns A Promise for the completion of the callback.
     */
    catch<TResult = never>(onrejected?: ((reason: any) => TResult | PromiseLike<TResult>) | undefined | null): $Utils.JsPromise<T | TResult>
    /**
     * Attaches a callback that is invoked when the Promise is settled (fulfilled or rejected). The
     * resolved value cannot be modified from the callback.
     * @param onfinally The callback to execute when the Promise is settled (fulfilled or rejected).
     * @returns A Promise for the completion of the callback.
     */
    finally(onfinally?: (() => void) | undefined | null): $Utils.JsPromise<T>
  }




  /**
   * Fields of the CheckInRecord model
   */
  interface CheckInRecordFieldRefs {
    readonly id: FieldRef<"CheckInRecord", 'String'>
    readonly checkInTime: FieldRef<"CheckInRecord", 'DateTime'>
    readonly checkOutTime: FieldRef<"CheckInRecord", 'DateTime'>
    readonly pickedUpBy: FieldRef<"CheckInRecord", 'String'>
    readonly childId: FieldRef<"CheckInRecord", 'String'>
    readonly sessionId: FieldRef<"CheckInRecord", 'String'>
    readonly checkInStaffId: FieldRef<"CheckInRecord", 'String'>
    readonly checkOutStaffId: FieldRef<"CheckInRecord", 'String'>
  }
    

  // Custom InputTypes
  /**
   * CheckInRecord findUnique
   */
  export type CheckInRecordFindUniqueArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the CheckInRecord
     */
    select?: CheckInRecordSelect<ExtArgs> | null
    /**
     * Omit specific fields from the CheckInRecord
     */
    omit?: CheckInRecordOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: CheckInRecordInclude<ExtArgs> | null
    /**
     * Filter, which CheckInRecord to fetch.
     */
    where: CheckInRecordWhereUniqueInput
  }

  /**
   * CheckInRecord findUniqueOrThrow
   */
  export type CheckInRecordFindUniqueOrThrowArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the CheckInRecord
     */
    select?: CheckInRecordSelect<ExtArgs> | null
    /**
     * Omit specific fields from the CheckInRecord
     */
    omit?: CheckInRecordOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: CheckInRecordInclude<ExtArgs> | null
    /**
     * Filter, which CheckInRecord to fetch.
     */
    where: CheckInRecordWhereUniqueInput
  }

  /**
   * CheckInRecord findFirst
   */
  export type CheckInRecordFindFirstArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the CheckInRecord
     */
    select?: CheckInRecordSelect<ExtArgs> | null
    /**
     * Omit specific fields from the CheckInRecord
     */
    omit?: CheckInRecordOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: CheckInRecordInclude<ExtArgs> | null
    /**
     * Filter, which CheckInRecord to fetch.
     */
    where?: CheckInRecordWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of CheckInRecords to fetch.
     */
    orderBy?: CheckInRecordOrderByWithRelationInput | CheckInRecordOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the position for searching for CheckInRecords.
     */
    cursor?: CheckInRecordWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` CheckInRecords from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` CheckInRecords.
     */
    skip?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/distinct Distinct Docs}
     * 
     * Filter by unique combinations of CheckInRecords.
     */
    distinct?: CheckInRecordScalarFieldEnum | CheckInRecordScalarFieldEnum[]
  }

  /**
   * CheckInRecord findFirstOrThrow
   */
  export type CheckInRecordFindFirstOrThrowArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the CheckInRecord
     */
    select?: CheckInRecordSelect<ExtArgs> | null
    /**
     * Omit specific fields from the CheckInRecord
     */
    omit?: CheckInRecordOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: CheckInRecordInclude<ExtArgs> | null
    /**
     * Filter, which CheckInRecord to fetch.
     */
    where?: CheckInRecordWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of CheckInRecords to fetch.
     */
    orderBy?: CheckInRecordOrderByWithRelationInput | CheckInRecordOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the position for searching for CheckInRecords.
     */
    cursor?: CheckInRecordWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` CheckInRecords from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` CheckInRecords.
     */
    skip?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/distinct Distinct Docs}
     * 
     * Filter by unique combinations of CheckInRecords.
     */
    distinct?: CheckInRecordScalarFieldEnum | CheckInRecordScalarFieldEnum[]
  }

  /**
   * CheckInRecord findMany
   */
  export type CheckInRecordFindManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the CheckInRecord
     */
    select?: CheckInRecordSelect<ExtArgs> | null
    /**
     * Omit specific fields from the CheckInRecord
     */
    omit?: CheckInRecordOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: CheckInRecordInclude<ExtArgs> | null
    /**
     * Filter, which CheckInRecords to fetch.
     */
    where?: CheckInRecordWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of CheckInRecords to fetch.
     */
    orderBy?: CheckInRecordOrderByWithRelationInput | CheckInRecordOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the position for listing CheckInRecords.
     */
    cursor?: CheckInRecordWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` CheckInRecords from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` CheckInRecords.
     */
    skip?: number
    distinct?: CheckInRecordScalarFieldEnum | CheckInRecordScalarFieldEnum[]
  }

  /**
   * CheckInRecord create
   */
  export type CheckInRecordCreateArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the CheckInRecord
     */
    select?: CheckInRecordSelect<ExtArgs> | null
    /**
     * Omit specific fields from the CheckInRecord
     */
    omit?: CheckInRecordOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: CheckInRecordInclude<ExtArgs> | null
    /**
     * The data needed to create a CheckInRecord.
     */
    data: XOR<CheckInRecordCreateInput, CheckInRecordUncheckedCreateInput>
  }

  /**
   * CheckInRecord createMany
   */
  export type CheckInRecordCreateManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * The data used to create many CheckInRecords.
     */
    data: CheckInRecordCreateManyInput | CheckInRecordCreateManyInput[]
    skipDuplicates?: boolean
  }

  /**
   * CheckInRecord createManyAndReturn
   */
  export type CheckInRecordCreateManyAndReturnArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the CheckInRecord
     */
    select?: CheckInRecordSelectCreateManyAndReturn<ExtArgs> | null
    /**
     * Omit specific fields from the CheckInRecord
     */
    omit?: CheckInRecordOmit<ExtArgs> | null
    /**
     * The data used to create many CheckInRecords.
     */
    data: CheckInRecordCreateManyInput | CheckInRecordCreateManyInput[]
    skipDuplicates?: boolean
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: CheckInRecordIncludeCreateManyAndReturn<ExtArgs> | null
  }

  /**
   * CheckInRecord update
   */
  export type CheckInRecordUpdateArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the CheckInRecord
     */
    select?: CheckInRecordSelect<ExtArgs> | null
    /**
     * Omit specific fields from the CheckInRecord
     */
    omit?: CheckInRecordOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: CheckInRecordInclude<ExtArgs> | null
    /**
     * The data needed to update a CheckInRecord.
     */
    data: XOR<CheckInRecordUpdateInput, CheckInRecordUncheckedUpdateInput>
    /**
     * Choose, which CheckInRecord to update.
     */
    where: CheckInRecordWhereUniqueInput
  }

  /**
   * CheckInRecord updateMany
   */
  export type CheckInRecordUpdateManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * The data used to update CheckInRecords.
     */
    data: XOR<CheckInRecordUpdateManyMutationInput, CheckInRecordUncheckedUpdateManyInput>
    /**
     * Filter which CheckInRecords to update
     */
    where?: CheckInRecordWhereInput
    /**
     * Limit how many CheckInRecords to update.
     */
    limit?: number
  }

  /**
   * CheckInRecord updateManyAndReturn
   */
  export type CheckInRecordUpdateManyAndReturnArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the CheckInRecord
     */
    select?: CheckInRecordSelectUpdateManyAndReturn<ExtArgs> | null
    /**
     * Omit specific fields from the CheckInRecord
     */
    omit?: CheckInRecordOmit<ExtArgs> | null
    /**
     * The data used to update CheckInRecords.
     */
    data: XOR<CheckInRecordUpdateManyMutationInput, CheckInRecordUncheckedUpdateManyInput>
    /**
     * Filter which CheckInRecords to update
     */
    where?: CheckInRecordWhereInput
    /**
     * Limit how many CheckInRecords to update.
     */
    limit?: number
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: CheckInRecordIncludeUpdateManyAndReturn<ExtArgs> | null
  }

  /**
   * CheckInRecord upsert
   */
  export type CheckInRecordUpsertArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the CheckInRecord
     */
    select?: CheckInRecordSelect<ExtArgs> | null
    /**
     * Omit specific fields from the CheckInRecord
     */
    omit?: CheckInRecordOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: CheckInRecordInclude<ExtArgs> | null
    /**
     * The filter to search for the CheckInRecord to update in case it exists.
     */
    where: CheckInRecordWhereUniqueInput
    /**
     * In case the CheckInRecord found by the `where` argument doesn't exist, create a new CheckInRecord with this data.
     */
    create: XOR<CheckInRecordCreateInput, CheckInRecordUncheckedCreateInput>
    /**
     * In case the CheckInRecord was found with the provided `where` argument, update it with this data.
     */
    update: XOR<CheckInRecordUpdateInput, CheckInRecordUncheckedUpdateInput>
  }

  /**
   * CheckInRecord delete
   */
  export type CheckInRecordDeleteArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the CheckInRecord
     */
    select?: CheckInRecordSelect<ExtArgs> | null
    /**
     * Omit specific fields from the CheckInRecord
     */
    omit?: CheckInRecordOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: CheckInRecordInclude<ExtArgs> | null
    /**
     * Filter which CheckInRecord to delete.
     */
    where: CheckInRecordWhereUniqueInput
  }

  /**
   * CheckInRecord deleteMany
   */
  export type CheckInRecordDeleteManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Filter which CheckInRecords to delete
     */
    where?: CheckInRecordWhereInput
    /**
     * Limit how many CheckInRecords to delete.
     */
    limit?: number
  }

  /**
   * CheckInRecord.checkOutStaff
   */
  export type CheckInRecord$checkOutStaffArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the AdminUser
     */
    select?: AdminUserSelect<ExtArgs> | null
    /**
     * Omit specific fields from the AdminUser
     */
    omit?: AdminUserOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: AdminUserInclude<ExtArgs> | null
    where?: AdminUserWhereInput
  }

  /**
   * CheckInRecord without action
   */
  export type CheckInRecordDefaultArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the CheckInRecord
     */
    select?: CheckInRecordSelect<ExtArgs> | null
    /**
     * Omit specific fields from the CheckInRecord
     */
    omit?: CheckInRecordOmit<ExtArgs> | null
    /**
     * Choose, which related nodes to fetch as well
     */
    include?: CheckInRecordInclude<ExtArgs> | null
  }


  /**
   * Model AuditLog
   */

  export type AggregateAuditLog = {
    _count: AuditLogCountAggregateOutputType | null
    _min: AuditLogMinAggregateOutputType | null
    _max: AuditLogMaxAggregateOutputType | null
  }

  export type AuditLogMinAggregateOutputType = {
    id: string | null
    timestamp: Date | null
    userId: string | null
    action: string | null
    entityType: string | null
    entityId: string | null
  }

  export type AuditLogMaxAggregateOutputType = {
    id: string | null
    timestamp: Date | null
    userId: string | null
    action: string | null
    entityType: string | null
    entityId: string | null
  }

  export type AuditLogCountAggregateOutputType = {
    id: number
    timestamp: number
    userId: number
    action: number
    entityType: number
    entityId: number
    details: number
    _all: number
  }


  export type AuditLogMinAggregateInputType = {
    id?: true
    timestamp?: true
    userId?: true
    action?: true
    entityType?: true
    entityId?: true
  }

  export type AuditLogMaxAggregateInputType = {
    id?: true
    timestamp?: true
    userId?: true
    action?: true
    entityType?: true
    entityId?: true
  }

  export type AuditLogCountAggregateInputType = {
    id?: true
    timestamp?: true
    userId?: true
    action?: true
    entityType?: true
    entityId?: true
    details?: true
    _all?: true
  }

  export type AuditLogAggregateArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Filter which AuditLog to aggregate.
     */
    where?: AuditLogWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of AuditLogs to fetch.
     */
    orderBy?: AuditLogOrderByWithRelationInput | AuditLogOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the start position
     */
    cursor?: AuditLogWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` AuditLogs from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` AuditLogs.
     */
    skip?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/aggregations Aggregation Docs}
     * 
     * Count returned AuditLogs
    **/
    _count?: true | AuditLogCountAggregateInputType
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/aggregations Aggregation Docs}
     * 
     * Select which fields to find the minimum value
    **/
    _min?: AuditLogMinAggregateInputType
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/aggregations Aggregation Docs}
     * 
     * Select which fields to find the maximum value
    **/
    _max?: AuditLogMaxAggregateInputType
  }

  export type GetAuditLogAggregateType<T extends AuditLogAggregateArgs> = {
        [P in keyof T & keyof AggregateAuditLog]: P extends '_count' | 'count'
      ? T[P] extends true
        ? number
        : GetScalarType<T[P], AggregateAuditLog[P]>
      : GetScalarType<T[P], AggregateAuditLog[P]>
  }




  export type AuditLogGroupByArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    where?: AuditLogWhereInput
    orderBy?: AuditLogOrderByWithAggregationInput | AuditLogOrderByWithAggregationInput[]
    by: AuditLogScalarFieldEnum[] | AuditLogScalarFieldEnum
    having?: AuditLogScalarWhereWithAggregatesInput
    take?: number
    skip?: number
    _count?: AuditLogCountAggregateInputType | true
    _min?: AuditLogMinAggregateInputType
    _max?: AuditLogMaxAggregateInputType
  }

  export type AuditLogGroupByOutputType = {
    id: string
    timestamp: Date
    userId: string
    action: string
    entityType: string
    entityId: string
    details: JsonValue | null
    _count: AuditLogCountAggregateOutputType | null
    _min: AuditLogMinAggregateOutputType | null
    _max: AuditLogMaxAggregateOutputType | null
  }

  type GetAuditLogGroupByPayload<T extends AuditLogGroupByArgs> = Prisma.PrismaPromise<
    Array<
      PickEnumerable<AuditLogGroupByOutputType, T['by']> &
        {
          [P in ((keyof T) & (keyof AuditLogGroupByOutputType))]: P extends '_count'
            ? T[P] extends boolean
              ? number
              : GetScalarType<T[P], AuditLogGroupByOutputType[P]>
            : GetScalarType<T[P], AuditLogGroupByOutputType[P]>
        }
      >
    >


  export type AuditLogSelect<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetSelect<{
    id?: boolean
    timestamp?: boolean
    userId?: boolean
    action?: boolean
    entityType?: boolean
    entityId?: boolean
    details?: boolean
  }, ExtArgs["result"]["auditLog"]>

  export type AuditLogSelectCreateManyAndReturn<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetSelect<{
    id?: boolean
    timestamp?: boolean
    userId?: boolean
    action?: boolean
    entityType?: boolean
    entityId?: boolean
    details?: boolean
  }, ExtArgs["result"]["auditLog"]>

  export type AuditLogSelectUpdateManyAndReturn<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetSelect<{
    id?: boolean
    timestamp?: boolean
    userId?: boolean
    action?: boolean
    entityType?: boolean
    entityId?: boolean
    details?: boolean
  }, ExtArgs["result"]["auditLog"]>

  export type AuditLogSelectScalar = {
    id?: boolean
    timestamp?: boolean
    userId?: boolean
    action?: boolean
    entityType?: boolean
    entityId?: boolean
    details?: boolean
  }

  export type AuditLogOmit<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = $Extensions.GetOmit<"id" | "timestamp" | "userId" | "action" | "entityType" | "entityId" | "details", ExtArgs["result"]["auditLog"]>

  export type $AuditLogPayload<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    name: "AuditLog"
    objects: {}
    scalars: $Extensions.GetPayloadResult<{
      id: string
      timestamp: Date
      userId: string
      action: string
      entityType: string
      entityId: string
      details: Prisma.JsonValue | null
    }, ExtArgs["result"]["auditLog"]>
    composites: {}
  }

  type AuditLogGetPayload<S extends boolean | null | undefined | AuditLogDefaultArgs> = $Result.GetResult<Prisma.$AuditLogPayload, S>

  type AuditLogCountArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> =
    Omit<AuditLogFindManyArgs, 'select' | 'include' | 'distinct' | 'omit'> & {
      select?: AuditLogCountAggregateInputType | true
    }

  export interface AuditLogDelegate<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs, GlobalOmitOptions = {}> {
    [K: symbol]: { types: Prisma.TypeMap<ExtArgs>['model']['AuditLog'], meta: { name: 'AuditLog' } }
    /**
     * Find zero or one AuditLog that matches the filter.
     * @param {AuditLogFindUniqueArgs} args - Arguments to find a AuditLog
     * @example
     * // Get one AuditLog
     * const auditLog = await prisma.auditLog.findUnique({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findUnique<T extends AuditLogFindUniqueArgs>(args: SelectSubset<T, AuditLogFindUniqueArgs<ExtArgs>>): Prisma__AuditLogClient<$Result.GetResult<Prisma.$AuditLogPayload<ExtArgs>, T, "findUnique", GlobalOmitOptions> | null, null, ExtArgs, GlobalOmitOptions>

    /**
     * Find one AuditLog that matches the filter or throw an error with `error.code='P2025'`
     * if no matches were found.
     * @param {AuditLogFindUniqueOrThrowArgs} args - Arguments to find a AuditLog
     * @example
     * // Get one AuditLog
     * const auditLog = await prisma.auditLog.findUniqueOrThrow({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findUniqueOrThrow<T extends AuditLogFindUniqueOrThrowArgs>(args: SelectSubset<T, AuditLogFindUniqueOrThrowArgs<ExtArgs>>): Prisma__AuditLogClient<$Result.GetResult<Prisma.$AuditLogPayload<ExtArgs>, T, "findUniqueOrThrow", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Find the first AuditLog that matches the filter.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {AuditLogFindFirstArgs} args - Arguments to find a AuditLog
     * @example
     * // Get one AuditLog
     * const auditLog = await prisma.auditLog.findFirst({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findFirst<T extends AuditLogFindFirstArgs>(args?: SelectSubset<T, AuditLogFindFirstArgs<ExtArgs>>): Prisma__AuditLogClient<$Result.GetResult<Prisma.$AuditLogPayload<ExtArgs>, T, "findFirst", GlobalOmitOptions> | null, null, ExtArgs, GlobalOmitOptions>

    /**
     * Find the first AuditLog that matches the filter or
     * throw `PrismaKnownClientError` with `P2025` code if no matches were found.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {AuditLogFindFirstOrThrowArgs} args - Arguments to find a AuditLog
     * @example
     * // Get one AuditLog
     * const auditLog = await prisma.auditLog.findFirstOrThrow({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     */
    findFirstOrThrow<T extends AuditLogFindFirstOrThrowArgs>(args?: SelectSubset<T, AuditLogFindFirstOrThrowArgs<ExtArgs>>): Prisma__AuditLogClient<$Result.GetResult<Prisma.$AuditLogPayload<ExtArgs>, T, "findFirstOrThrow", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Find zero or more AuditLogs that matches the filter.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {AuditLogFindManyArgs} args - Arguments to filter and select certain fields only.
     * @example
     * // Get all AuditLogs
     * const auditLogs = await prisma.auditLog.findMany()
     * 
     * // Get first 10 AuditLogs
     * const auditLogs = await prisma.auditLog.findMany({ take: 10 })
     * 
     * // Only select the `id`
     * const auditLogWithIdOnly = await prisma.auditLog.findMany({ select: { id: true } })
     * 
     */
    findMany<T extends AuditLogFindManyArgs>(args?: SelectSubset<T, AuditLogFindManyArgs<ExtArgs>>): Prisma.PrismaPromise<$Result.GetResult<Prisma.$AuditLogPayload<ExtArgs>, T, "findMany", GlobalOmitOptions>>

    /**
     * Create a AuditLog.
     * @param {AuditLogCreateArgs} args - Arguments to create a AuditLog.
     * @example
     * // Create one AuditLog
     * const AuditLog = await prisma.auditLog.create({
     *   data: {
     *     // ... data to create a AuditLog
     *   }
     * })
     * 
     */
    create<T extends AuditLogCreateArgs>(args: SelectSubset<T, AuditLogCreateArgs<ExtArgs>>): Prisma__AuditLogClient<$Result.GetResult<Prisma.$AuditLogPayload<ExtArgs>, T, "create", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Create many AuditLogs.
     * @param {AuditLogCreateManyArgs} args - Arguments to create many AuditLogs.
     * @example
     * // Create many AuditLogs
     * const auditLog = await prisma.auditLog.createMany({
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     *     
     */
    createMany<T extends AuditLogCreateManyArgs>(args?: SelectSubset<T, AuditLogCreateManyArgs<ExtArgs>>): Prisma.PrismaPromise<BatchPayload>

    /**
     * Create many AuditLogs and returns the data saved in the database.
     * @param {AuditLogCreateManyAndReturnArgs} args - Arguments to create many AuditLogs.
     * @example
     * // Create many AuditLogs
     * const auditLog = await prisma.auditLog.createManyAndReturn({
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * 
     * // Create many AuditLogs and only return the `id`
     * const auditLogWithIdOnly = await prisma.auditLog.createManyAndReturn({
     *   select: { id: true },
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * 
     */
    createManyAndReturn<T extends AuditLogCreateManyAndReturnArgs>(args?: SelectSubset<T, AuditLogCreateManyAndReturnArgs<ExtArgs>>): Prisma.PrismaPromise<$Result.GetResult<Prisma.$AuditLogPayload<ExtArgs>, T, "createManyAndReturn", GlobalOmitOptions>>

    /**
     * Delete a AuditLog.
     * @param {AuditLogDeleteArgs} args - Arguments to delete one AuditLog.
     * @example
     * // Delete one AuditLog
     * const AuditLog = await prisma.auditLog.delete({
     *   where: {
     *     // ... filter to delete one AuditLog
     *   }
     * })
     * 
     */
    delete<T extends AuditLogDeleteArgs>(args: SelectSubset<T, AuditLogDeleteArgs<ExtArgs>>): Prisma__AuditLogClient<$Result.GetResult<Prisma.$AuditLogPayload<ExtArgs>, T, "delete", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Update one AuditLog.
     * @param {AuditLogUpdateArgs} args - Arguments to update one AuditLog.
     * @example
     * // Update one AuditLog
     * const auditLog = await prisma.auditLog.update({
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: {
     *     // ... provide data here
     *   }
     * })
     * 
     */
    update<T extends AuditLogUpdateArgs>(args: SelectSubset<T, AuditLogUpdateArgs<ExtArgs>>): Prisma__AuditLogClient<$Result.GetResult<Prisma.$AuditLogPayload<ExtArgs>, T, "update", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>

    /**
     * Delete zero or more AuditLogs.
     * @param {AuditLogDeleteManyArgs} args - Arguments to filter AuditLogs to delete.
     * @example
     * // Delete a few AuditLogs
     * const { count } = await prisma.auditLog.deleteMany({
     *   where: {
     *     // ... provide filter here
     *   }
     * })
     * 
     */
    deleteMany<T extends AuditLogDeleteManyArgs>(args?: SelectSubset<T, AuditLogDeleteManyArgs<ExtArgs>>): Prisma.PrismaPromise<BatchPayload>

    /**
     * Update zero or more AuditLogs.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {AuditLogUpdateManyArgs} args - Arguments to update one or more rows.
     * @example
     * // Update many AuditLogs
     * const auditLog = await prisma.auditLog.updateMany({
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: {
     *     // ... provide data here
     *   }
     * })
     * 
     */
    updateMany<T extends AuditLogUpdateManyArgs>(args: SelectSubset<T, AuditLogUpdateManyArgs<ExtArgs>>): Prisma.PrismaPromise<BatchPayload>

    /**
     * Update zero or more AuditLogs and returns the data updated in the database.
     * @param {AuditLogUpdateManyAndReturnArgs} args - Arguments to update many AuditLogs.
     * @example
     * // Update many AuditLogs
     * const auditLog = await prisma.auditLog.updateManyAndReturn({
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * 
     * // Update zero or more AuditLogs and only return the `id`
     * const auditLogWithIdOnly = await prisma.auditLog.updateManyAndReturn({
     *   select: { id: true },
     *   where: {
     *     // ... provide filter here
     *   },
     *   data: [
     *     // ... provide data here
     *   ]
     * })
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * 
     */
    updateManyAndReturn<T extends AuditLogUpdateManyAndReturnArgs>(args: SelectSubset<T, AuditLogUpdateManyAndReturnArgs<ExtArgs>>): Prisma.PrismaPromise<$Result.GetResult<Prisma.$AuditLogPayload<ExtArgs>, T, "updateManyAndReturn", GlobalOmitOptions>>

    /**
     * Create or update one AuditLog.
     * @param {AuditLogUpsertArgs} args - Arguments to update or create a AuditLog.
     * @example
     * // Update or create a AuditLog
     * const auditLog = await prisma.auditLog.upsert({
     *   create: {
     *     // ... data to create a AuditLog
     *   },
     *   update: {
     *     // ... in case it already exists, update
     *   },
     *   where: {
     *     // ... the filter for the AuditLog we want to update
     *   }
     * })
     */
    upsert<T extends AuditLogUpsertArgs>(args: SelectSubset<T, AuditLogUpsertArgs<ExtArgs>>): Prisma__AuditLogClient<$Result.GetResult<Prisma.$AuditLogPayload<ExtArgs>, T, "upsert", GlobalOmitOptions>, never, ExtArgs, GlobalOmitOptions>


    /**
     * Count the number of AuditLogs.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {AuditLogCountArgs} args - Arguments to filter AuditLogs to count.
     * @example
     * // Count the number of AuditLogs
     * const count = await prisma.auditLog.count({
     *   where: {
     *     // ... the filter for the AuditLogs we want to count
     *   }
     * })
    **/
    count<T extends AuditLogCountArgs>(
      args?: Subset<T, AuditLogCountArgs>,
    ): Prisma.PrismaPromise<
      T extends $Utils.Record<'select', any>
        ? T['select'] extends true
          ? number
          : GetScalarType<T['select'], AuditLogCountAggregateOutputType>
        : number
    >

    /**
     * Allows you to perform aggregations operations on a AuditLog.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {AuditLogAggregateArgs} args - Select which aggregations you would like to apply and on what fields.
     * @example
     * // Ordered by age ascending
     * // Where email contains prisma.io
     * // Limited to the 10 users
     * const aggregations = await prisma.user.aggregate({
     *   _avg: {
     *     age: true,
     *   },
     *   where: {
     *     email: {
     *       contains: "prisma.io",
     *     },
     *   },
     *   orderBy: {
     *     age: "asc",
     *   },
     *   take: 10,
     * })
    **/
    aggregate<T extends AuditLogAggregateArgs>(args: Subset<T, AuditLogAggregateArgs>): Prisma.PrismaPromise<GetAuditLogAggregateType<T>>

    /**
     * Group by AuditLog.
     * Note, that providing `undefined` is treated as the value not being there.
     * Read more here: https://pris.ly/d/null-undefined
     * @param {AuditLogGroupByArgs} args - Group by arguments.
     * @example
     * // Group by city, order by createdAt, get count
     * const result = await prisma.user.groupBy({
     *   by: ['city', 'createdAt'],
     *   orderBy: {
     *     createdAt: true
     *   },
     *   _count: {
     *     _all: true
     *   },
     * })
     * 
    **/
    groupBy<
      T extends AuditLogGroupByArgs,
      HasSelectOrTake extends Or<
        Extends<'skip', Keys<T>>,
        Extends<'take', Keys<T>>
      >,
      OrderByArg extends True extends HasSelectOrTake
        ? { orderBy: AuditLogGroupByArgs['orderBy'] }
        : { orderBy?: AuditLogGroupByArgs['orderBy'] },
      OrderFields extends ExcludeUnderscoreKeys<Keys<MaybeTupleToUnion<T['orderBy']>>>,
      ByFields extends MaybeTupleToUnion<T['by']>,
      ByValid extends Has<ByFields, OrderFields>,
      HavingFields extends GetHavingFields<T['having']>,
      HavingValid extends Has<ByFields, HavingFields>,
      ByEmpty extends T['by'] extends never[] ? True : False,
      InputErrors extends ByEmpty extends True
      ? `Error: "by" must not be empty.`
      : HavingValid extends False
      ? {
          [P in HavingFields]: P extends ByFields
            ? never
            : P extends string
            ? `Error: Field "${P}" used in "having" needs to be provided in "by".`
            : [
                Error,
                'Field ',
                P,
                ` in "having" needs to be provided in "by"`,
              ]
        }[HavingFields]
      : 'take' extends Keys<T>
      ? 'orderBy' extends Keys<T>
        ? ByValid extends True
          ? {}
          : {
              [P in OrderFields]: P extends ByFields
                ? never
                : `Error: Field "${P}" in "orderBy" needs to be provided in "by"`
            }[OrderFields]
        : 'Error: If you provide "take", you also need to provide "orderBy"'
      : 'skip' extends Keys<T>
      ? 'orderBy' extends Keys<T>
        ? ByValid extends True
          ? {}
          : {
              [P in OrderFields]: P extends ByFields
                ? never
                : `Error: Field "${P}" in "orderBy" needs to be provided in "by"`
            }[OrderFields]
        : 'Error: If you provide "skip", you also need to provide "orderBy"'
      : ByValid extends True
      ? {}
      : {
          [P in OrderFields]: P extends ByFields
            ? never
            : `Error: Field "${P}" in "orderBy" needs to be provided in "by"`
        }[OrderFields]
    >(args: SubsetIntersection<T, AuditLogGroupByArgs, OrderByArg> & InputErrors): {} extends InputErrors ? GetAuditLogGroupByPayload<T> : Prisma.PrismaPromise<InputErrors>
  /**
   * Fields of the AuditLog model
   */
  readonly fields: AuditLogFieldRefs;
  }

  /**
   * The delegate class that acts as a "Promise-like" for AuditLog.
   * Why is this prefixed with `Prisma__`?
   * Because we want to prevent naming conflicts as mentioned in
   * https://github.com/prisma/prisma-client-js/issues/707
   */
  export interface Prisma__AuditLogClient<T, Null = never, ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs, GlobalOmitOptions = {}> extends Prisma.PrismaPromise<T> {
    readonly [Symbol.toStringTag]: "PrismaPromise"
    /**
     * Attaches callbacks for the resolution and/or rejection of the Promise.
     * @param onfulfilled The callback to execute when the Promise is resolved.
     * @param onrejected The callback to execute when the Promise is rejected.
     * @returns A Promise for the completion of which ever callback is executed.
     */
    then<TResult1 = T, TResult2 = never>(onfulfilled?: ((value: T) => TResult1 | PromiseLike<TResult1>) | undefined | null, onrejected?: ((reason: any) => TResult2 | PromiseLike<TResult2>) | undefined | null): $Utils.JsPromise<TResult1 | TResult2>
    /**
     * Attaches a callback for only the rejection of the Promise.
     * @param onrejected The callback to execute when the Promise is rejected.
     * @returns A Promise for the completion of the callback.
     */
    catch<TResult = never>(onrejected?: ((reason: any) => TResult | PromiseLike<TResult>) | undefined | null): $Utils.JsPromise<T | TResult>
    /**
     * Attaches a callback that is invoked when the Promise is settled (fulfilled or rejected). The
     * resolved value cannot be modified from the callback.
     * @param onfinally The callback to execute when the Promise is settled (fulfilled or rejected).
     * @returns A Promise for the completion of the callback.
     */
    finally(onfinally?: (() => void) | undefined | null): $Utils.JsPromise<T>
  }




  /**
   * Fields of the AuditLog model
   */
  interface AuditLogFieldRefs {
    readonly id: FieldRef<"AuditLog", 'String'>
    readonly timestamp: FieldRef<"AuditLog", 'DateTime'>
    readonly userId: FieldRef<"AuditLog", 'String'>
    readonly action: FieldRef<"AuditLog", 'String'>
    readonly entityType: FieldRef<"AuditLog", 'String'>
    readonly entityId: FieldRef<"AuditLog", 'String'>
    readonly details: FieldRef<"AuditLog", 'Json'>
  }
    

  // Custom InputTypes
  /**
   * AuditLog findUnique
   */
  export type AuditLogFindUniqueArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the AuditLog
     */
    select?: AuditLogSelect<ExtArgs> | null
    /**
     * Omit specific fields from the AuditLog
     */
    omit?: AuditLogOmit<ExtArgs> | null
    /**
     * Filter, which AuditLog to fetch.
     */
    where: AuditLogWhereUniqueInput
  }

  /**
   * AuditLog findUniqueOrThrow
   */
  export type AuditLogFindUniqueOrThrowArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the AuditLog
     */
    select?: AuditLogSelect<ExtArgs> | null
    /**
     * Omit specific fields from the AuditLog
     */
    omit?: AuditLogOmit<ExtArgs> | null
    /**
     * Filter, which AuditLog to fetch.
     */
    where: AuditLogWhereUniqueInput
  }

  /**
   * AuditLog findFirst
   */
  export type AuditLogFindFirstArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the AuditLog
     */
    select?: AuditLogSelect<ExtArgs> | null
    /**
     * Omit specific fields from the AuditLog
     */
    omit?: AuditLogOmit<ExtArgs> | null
    /**
     * Filter, which AuditLog to fetch.
     */
    where?: AuditLogWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of AuditLogs to fetch.
     */
    orderBy?: AuditLogOrderByWithRelationInput | AuditLogOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the position for searching for AuditLogs.
     */
    cursor?: AuditLogWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` AuditLogs from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` AuditLogs.
     */
    skip?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/distinct Distinct Docs}
     * 
     * Filter by unique combinations of AuditLogs.
     */
    distinct?: AuditLogScalarFieldEnum | AuditLogScalarFieldEnum[]
  }

  /**
   * AuditLog findFirstOrThrow
   */
  export type AuditLogFindFirstOrThrowArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the AuditLog
     */
    select?: AuditLogSelect<ExtArgs> | null
    /**
     * Omit specific fields from the AuditLog
     */
    omit?: AuditLogOmit<ExtArgs> | null
    /**
     * Filter, which AuditLog to fetch.
     */
    where?: AuditLogWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of AuditLogs to fetch.
     */
    orderBy?: AuditLogOrderByWithRelationInput | AuditLogOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the position for searching for AuditLogs.
     */
    cursor?: AuditLogWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` AuditLogs from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` AuditLogs.
     */
    skip?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/distinct Distinct Docs}
     * 
     * Filter by unique combinations of AuditLogs.
     */
    distinct?: AuditLogScalarFieldEnum | AuditLogScalarFieldEnum[]
  }

  /**
   * AuditLog findMany
   */
  export type AuditLogFindManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the AuditLog
     */
    select?: AuditLogSelect<ExtArgs> | null
    /**
     * Omit specific fields from the AuditLog
     */
    omit?: AuditLogOmit<ExtArgs> | null
    /**
     * Filter, which AuditLogs to fetch.
     */
    where?: AuditLogWhereInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/sorting Sorting Docs}
     * 
     * Determine the order of AuditLogs to fetch.
     */
    orderBy?: AuditLogOrderByWithRelationInput | AuditLogOrderByWithRelationInput[]
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination#cursor-based-pagination Cursor Docs}
     * 
     * Sets the position for listing AuditLogs.
     */
    cursor?: AuditLogWhereUniqueInput
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Take `±n` AuditLogs from the position of the cursor.
     */
    take?: number
    /**
     * {@link https://www.prisma.io/docs/concepts/components/prisma-client/pagination Pagination Docs}
     * 
     * Skip the first `n` AuditLogs.
     */
    skip?: number
    distinct?: AuditLogScalarFieldEnum | AuditLogScalarFieldEnum[]
  }

  /**
   * AuditLog create
   */
  export type AuditLogCreateArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the AuditLog
     */
    select?: AuditLogSelect<ExtArgs> | null
    /**
     * Omit specific fields from the AuditLog
     */
    omit?: AuditLogOmit<ExtArgs> | null
    /**
     * The data needed to create a AuditLog.
     */
    data: XOR<AuditLogCreateInput, AuditLogUncheckedCreateInput>
  }

  /**
   * AuditLog createMany
   */
  export type AuditLogCreateManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * The data used to create many AuditLogs.
     */
    data: AuditLogCreateManyInput | AuditLogCreateManyInput[]
    skipDuplicates?: boolean
  }

  /**
   * AuditLog createManyAndReturn
   */
  export type AuditLogCreateManyAndReturnArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the AuditLog
     */
    select?: AuditLogSelectCreateManyAndReturn<ExtArgs> | null
    /**
     * Omit specific fields from the AuditLog
     */
    omit?: AuditLogOmit<ExtArgs> | null
    /**
     * The data used to create many AuditLogs.
     */
    data: AuditLogCreateManyInput | AuditLogCreateManyInput[]
    skipDuplicates?: boolean
  }

  /**
   * AuditLog update
   */
  export type AuditLogUpdateArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the AuditLog
     */
    select?: AuditLogSelect<ExtArgs> | null
    /**
     * Omit specific fields from the AuditLog
     */
    omit?: AuditLogOmit<ExtArgs> | null
    /**
     * The data needed to update a AuditLog.
     */
    data: XOR<AuditLogUpdateInput, AuditLogUncheckedUpdateInput>
    /**
     * Choose, which AuditLog to update.
     */
    where: AuditLogWhereUniqueInput
  }

  /**
   * AuditLog updateMany
   */
  export type AuditLogUpdateManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * The data used to update AuditLogs.
     */
    data: XOR<AuditLogUpdateManyMutationInput, AuditLogUncheckedUpdateManyInput>
    /**
     * Filter which AuditLogs to update
     */
    where?: AuditLogWhereInput
    /**
     * Limit how many AuditLogs to update.
     */
    limit?: number
  }

  /**
   * AuditLog updateManyAndReturn
   */
  export type AuditLogUpdateManyAndReturnArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the AuditLog
     */
    select?: AuditLogSelectUpdateManyAndReturn<ExtArgs> | null
    /**
     * Omit specific fields from the AuditLog
     */
    omit?: AuditLogOmit<ExtArgs> | null
    /**
     * The data used to update AuditLogs.
     */
    data: XOR<AuditLogUpdateManyMutationInput, AuditLogUncheckedUpdateManyInput>
    /**
     * Filter which AuditLogs to update
     */
    where?: AuditLogWhereInput
    /**
     * Limit how many AuditLogs to update.
     */
    limit?: number
  }

  /**
   * AuditLog upsert
   */
  export type AuditLogUpsertArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the AuditLog
     */
    select?: AuditLogSelect<ExtArgs> | null
    /**
     * Omit specific fields from the AuditLog
     */
    omit?: AuditLogOmit<ExtArgs> | null
    /**
     * The filter to search for the AuditLog to update in case it exists.
     */
    where: AuditLogWhereUniqueInput
    /**
     * In case the AuditLog found by the `where` argument doesn't exist, create a new AuditLog with this data.
     */
    create: XOR<AuditLogCreateInput, AuditLogUncheckedCreateInput>
    /**
     * In case the AuditLog was found with the provided `where` argument, update it with this data.
     */
    update: XOR<AuditLogUpdateInput, AuditLogUncheckedUpdateInput>
  }

  /**
   * AuditLog delete
   */
  export type AuditLogDeleteArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the AuditLog
     */
    select?: AuditLogSelect<ExtArgs> | null
    /**
     * Omit specific fields from the AuditLog
     */
    omit?: AuditLogOmit<ExtArgs> | null
    /**
     * Filter which AuditLog to delete.
     */
    where: AuditLogWhereUniqueInput
  }

  /**
   * AuditLog deleteMany
   */
  export type AuditLogDeleteManyArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Filter which AuditLogs to delete
     */
    where?: AuditLogWhereInput
    /**
     * Limit how many AuditLogs to delete.
     */
    limit?: number
  }

  /**
   * AuditLog without action
   */
  export type AuditLogDefaultArgs<ExtArgs extends $Extensions.InternalArgs = $Extensions.DefaultArgs> = {
    /**
     * Select specific fields to fetch from the AuditLog
     */
    select?: AuditLogSelect<ExtArgs> | null
    /**
     * Omit specific fields from the AuditLog
     */
    omit?: AuditLogOmit<ExtArgs> | null
  }


  /**
   * Enums
   */

  export const TransactionIsolationLevel: {
    ReadUncommitted: 'ReadUncommitted',
    ReadCommitted: 'ReadCommitted',
    RepeatableRead: 'RepeatableRead',
    Serializable: 'Serializable'
  };

  export type TransactionIsolationLevel = (typeof TransactionIsolationLevel)[keyof typeof TransactionIsolationLevel]


  export const AdminUserScalarFieldEnum: {
    id: 'id',
    username: 'username',
    passwordHash: 'passwordHash',
    name: 'name',
    createdAt: 'createdAt',
    lastLogin: 'lastLogin',
    isActive: 'isActive'
  };

  export type AdminUserScalarFieldEnum = (typeof AdminUserScalarFieldEnum)[keyof typeof AdminUserScalarFieldEnum]


  export const FamilyScalarFieldEnum: {
    id: 'id',
    lastParticipationDate: 'lastParticipationDate'
  };

  export type FamilyScalarFieldEnum = (typeof FamilyScalarFieldEnum)[keyof typeof FamilyScalarFieldEnum]


  export const ParentScalarFieldEnum: {
    id: 'id',
    name: 'name',
    phone: 'phone',
    email: 'email',
    relationshipType: 'relationshipType',
    lastParticipationDate: 'lastParticipationDate',
    familyId: 'familyId'
  };

  export type ParentScalarFieldEnum = (typeof ParentScalarFieldEnum)[keyof typeof ParentScalarFieldEnum]


  export const ChildScalarFieldEnum: {
    id: 'id',
    firstName: 'firstName',
    lastName: 'lastName',
    birthdate: 'birthdate',
    allergies: 'allergies',
    notes: 'notes',
    qrToken: 'qrToken',
    lastParticipationDate: 'lastParticipationDate',
    familyId: 'familyId'
  };

  export type ChildScalarFieldEnum = (typeof ChildScalarFieldEnum)[keyof typeof ChildScalarFieldEnum]


  export const EventScalarFieldEnum: {
    id: 'id',
    name: 'name',
    startDate: 'startDate',
    endDate: 'endDate'
  };

  export type EventScalarFieldEnum = (typeof EventScalarFieldEnum)[keyof typeof EventScalarFieldEnum]


  export const SessionScalarFieldEnum: {
    id: 'id',
    name: 'name',
    startTime: 'startTime',
    endTime: 'endTime',
    isActive: 'isActive',
    requiresTicket: 'requiresTicket',
    eventId: 'eventId'
  };

  export type SessionScalarFieldEnum = (typeof SessionScalarFieldEnum)[keyof typeof SessionScalarFieldEnum]


  export const TicketScalarFieldEnum: {
    id: 'id',
    type: 'type',
    childId: 'childId',
    sessionId: 'sessionId'
  };

  export type TicketScalarFieldEnum = (typeof TicketScalarFieldEnum)[keyof typeof TicketScalarFieldEnum]


  export const CheckInRecordScalarFieldEnum: {
    id: 'id',
    checkInTime: 'checkInTime',
    checkOutTime: 'checkOutTime',
    pickedUpBy: 'pickedUpBy',
    childId: 'childId',
    sessionId: 'sessionId',
    checkInStaffId: 'checkInStaffId',
    checkOutStaffId: 'checkOutStaffId'
  };

  export type CheckInRecordScalarFieldEnum = (typeof CheckInRecordScalarFieldEnum)[keyof typeof CheckInRecordScalarFieldEnum]


  export const AuditLogScalarFieldEnum: {
    id: 'id',
    timestamp: 'timestamp',
    userId: 'userId',
    action: 'action',
    entityType: 'entityType',
    entityId: 'entityId',
    details: 'details'
  };

  export type AuditLogScalarFieldEnum = (typeof AuditLogScalarFieldEnum)[keyof typeof AuditLogScalarFieldEnum]


  export const SortOrder: {
    asc: 'asc',
    desc: 'desc'
  };

  export type SortOrder = (typeof SortOrder)[keyof typeof SortOrder]


  export const NullableJsonNullValueInput: {
    DbNull: typeof DbNull,
    JsonNull: typeof JsonNull
  };

  export type NullableJsonNullValueInput = (typeof NullableJsonNullValueInput)[keyof typeof NullableJsonNullValueInput]


  export const QueryMode: {
    default: 'default',
    insensitive: 'insensitive'
  };

  export type QueryMode = (typeof QueryMode)[keyof typeof QueryMode]


  export const NullsOrder: {
    first: 'first',
    last: 'last'
  };

  export type NullsOrder = (typeof NullsOrder)[keyof typeof NullsOrder]


  export const JsonNullValueFilter: {
    DbNull: typeof DbNull,
    JsonNull: typeof JsonNull,
    AnyNull: typeof AnyNull
  };

  export type JsonNullValueFilter = (typeof JsonNullValueFilter)[keyof typeof JsonNullValueFilter]


  /**
   * Field references
   */


  /**
   * Reference to a field of type 'String'
   */
  export type StringFieldRefInput<$PrismaModel> = FieldRefInputType<$PrismaModel, 'String'>
    


  /**
   * Reference to a field of type 'String[]'
   */
  export type ListStringFieldRefInput<$PrismaModel> = FieldRefInputType<$PrismaModel, 'String[]'>
    


  /**
   * Reference to a field of type 'DateTime'
   */
  export type DateTimeFieldRefInput<$PrismaModel> = FieldRefInputType<$PrismaModel, 'DateTime'>
    


  /**
   * Reference to a field of type 'DateTime[]'
   */
  export type ListDateTimeFieldRefInput<$PrismaModel> = FieldRefInputType<$PrismaModel, 'DateTime[]'>
    


  /**
   * Reference to a field of type 'Boolean'
   */
  export type BooleanFieldRefInput<$PrismaModel> = FieldRefInputType<$PrismaModel, 'Boolean'>
    


  /**
   * Reference to a field of type 'Json'
   */
  export type JsonFieldRefInput<$PrismaModel> = FieldRefInputType<$PrismaModel, 'Json'>
    


  /**
   * Reference to a field of type 'QueryMode'
   */
  export type EnumQueryModeFieldRefInput<$PrismaModel> = FieldRefInputType<$PrismaModel, 'QueryMode'>
    


  /**
   * Reference to a field of type 'Int'
   */
  export type IntFieldRefInput<$PrismaModel> = FieldRefInputType<$PrismaModel, 'Int'>
    


  /**
   * Reference to a field of type 'Int[]'
   */
  export type ListIntFieldRefInput<$PrismaModel> = FieldRefInputType<$PrismaModel, 'Int[]'>
    
  /**
   * Deep Input Types
   */


  export type AdminUserWhereInput = {
    AND?: AdminUserWhereInput | AdminUserWhereInput[]
    OR?: AdminUserWhereInput[]
    NOT?: AdminUserWhereInput | AdminUserWhereInput[]
    id?: StringFilter<"AdminUser"> | string
    username?: StringFilter<"AdminUser"> | string
    passwordHash?: StringFilter<"AdminUser"> | string
    name?: StringFilter<"AdminUser"> | string
    createdAt?: DateTimeFilter<"AdminUser"> | Date | string
    lastLogin?: DateTimeNullableFilter<"AdminUser"> | Date | string | null
    isActive?: BoolFilter<"AdminUser"> | boolean
    checkInsPerformed?: CheckInRecordListRelationFilter
    checkOutsPerformed?: CheckInRecordListRelationFilter
  }

  export type AdminUserOrderByWithRelationInput = {
    id?: SortOrder
    username?: SortOrder
    passwordHash?: SortOrder
    name?: SortOrder
    createdAt?: SortOrder
    lastLogin?: SortOrderInput | SortOrder
    isActive?: SortOrder
    checkInsPerformed?: CheckInRecordOrderByRelationAggregateInput
    checkOutsPerformed?: CheckInRecordOrderByRelationAggregateInput
  }

  export type AdminUserWhereUniqueInput = Prisma.AtLeast<{
    id?: string
    username?: string
    AND?: AdminUserWhereInput | AdminUserWhereInput[]
    OR?: AdminUserWhereInput[]
    NOT?: AdminUserWhereInput | AdminUserWhereInput[]
    passwordHash?: StringFilter<"AdminUser"> | string
    name?: StringFilter<"AdminUser"> | string
    createdAt?: DateTimeFilter<"AdminUser"> | Date | string
    lastLogin?: DateTimeNullableFilter<"AdminUser"> | Date | string | null
    isActive?: BoolFilter<"AdminUser"> | boolean
    checkInsPerformed?: CheckInRecordListRelationFilter
    checkOutsPerformed?: CheckInRecordListRelationFilter
  }, "id" | "username">

  export type AdminUserOrderByWithAggregationInput = {
    id?: SortOrder
    username?: SortOrder
    passwordHash?: SortOrder
    name?: SortOrder
    createdAt?: SortOrder
    lastLogin?: SortOrderInput | SortOrder
    isActive?: SortOrder
    _count?: AdminUserCountOrderByAggregateInput
    _max?: AdminUserMaxOrderByAggregateInput
    _min?: AdminUserMinOrderByAggregateInput
  }

  export type AdminUserScalarWhereWithAggregatesInput = {
    AND?: AdminUserScalarWhereWithAggregatesInput | AdminUserScalarWhereWithAggregatesInput[]
    OR?: AdminUserScalarWhereWithAggregatesInput[]
    NOT?: AdminUserScalarWhereWithAggregatesInput | AdminUserScalarWhereWithAggregatesInput[]
    id?: StringWithAggregatesFilter<"AdminUser"> | string
    username?: StringWithAggregatesFilter<"AdminUser"> | string
    passwordHash?: StringWithAggregatesFilter<"AdminUser"> | string
    name?: StringWithAggregatesFilter<"AdminUser"> | string
    createdAt?: DateTimeWithAggregatesFilter<"AdminUser"> | Date | string
    lastLogin?: DateTimeNullableWithAggregatesFilter<"AdminUser"> | Date | string | null
    isActive?: BoolWithAggregatesFilter<"AdminUser"> | boolean
  }

  export type FamilyWhereInput = {
    AND?: FamilyWhereInput | FamilyWhereInput[]
    OR?: FamilyWhereInput[]
    NOT?: FamilyWhereInput | FamilyWhereInput[]
    id?: StringFilter<"Family"> | string
    lastParticipationDate?: DateTimeNullableFilter<"Family"> | Date | string | null
    parents?: ParentListRelationFilter
    children?: ChildListRelationFilter
  }

  export type FamilyOrderByWithRelationInput = {
    id?: SortOrder
    lastParticipationDate?: SortOrderInput | SortOrder
    parents?: ParentOrderByRelationAggregateInput
    children?: ChildOrderByRelationAggregateInput
  }

  export type FamilyWhereUniqueInput = Prisma.AtLeast<{
    id?: string
    AND?: FamilyWhereInput | FamilyWhereInput[]
    OR?: FamilyWhereInput[]
    NOT?: FamilyWhereInput | FamilyWhereInput[]
    lastParticipationDate?: DateTimeNullableFilter<"Family"> | Date | string | null
    parents?: ParentListRelationFilter
    children?: ChildListRelationFilter
  }, "id">

  export type FamilyOrderByWithAggregationInput = {
    id?: SortOrder
    lastParticipationDate?: SortOrderInput | SortOrder
    _count?: FamilyCountOrderByAggregateInput
    _max?: FamilyMaxOrderByAggregateInput
    _min?: FamilyMinOrderByAggregateInput
  }

  export type FamilyScalarWhereWithAggregatesInput = {
    AND?: FamilyScalarWhereWithAggregatesInput | FamilyScalarWhereWithAggregatesInput[]
    OR?: FamilyScalarWhereWithAggregatesInput[]
    NOT?: FamilyScalarWhereWithAggregatesInput | FamilyScalarWhereWithAggregatesInput[]
    id?: StringWithAggregatesFilter<"Family"> | string
    lastParticipationDate?: DateTimeNullableWithAggregatesFilter<"Family"> | Date | string | null
  }

  export type ParentWhereInput = {
    AND?: ParentWhereInput | ParentWhereInput[]
    OR?: ParentWhereInput[]
    NOT?: ParentWhereInput | ParentWhereInput[]
    id?: StringFilter<"Parent"> | string
    name?: StringFilter<"Parent"> | string
    phone?: StringNullableFilter<"Parent"> | string | null
    email?: StringNullableFilter<"Parent"> | string | null
    relationshipType?: StringFilter<"Parent"> | string
    lastParticipationDate?: DateTimeNullableFilter<"Parent"> | Date | string | null
    familyId?: StringFilter<"Parent"> | string
    family?: XOR<FamilyScalarRelationFilter, FamilyWhereInput>
  }

  export type ParentOrderByWithRelationInput = {
    id?: SortOrder
    name?: SortOrder
    phone?: SortOrderInput | SortOrder
    email?: SortOrderInput | SortOrder
    relationshipType?: SortOrder
    lastParticipationDate?: SortOrderInput | SortOrder
    familyId?: SortOrder
    family?: FamilyOrderByWithRelationInput
  }

  export type ParentWhereUniqueInput = Prisma.AtLeast<{
    id?: string
    AND?: ParentWhereInput | ParentWhereInput[]
    OR?: ParentWhereInput[]
    NOT?: ParentWhereInput | ParentWhereInput[]
    name?: StringFilter<"Parent"> | string
    phone?: StringNullableFilter<"Parent"> | string | null
    email?: StringNullableFilter<"Parent"> | string | null
    relationshipType?: StringFilter<"Parent"> | string
    lastParticipationDate?: DateTimeNullableFilter<"Parent"> | Date | string | null
    familyId?: StringFilter<"Parent"> | string
    family?: XOR<FamilyScalarRelationFilter, FamilyWhereInput>
  }, "id">

  export type ParentOrderByWithAggregationInput = {
    id?: SortOrder
    name?: SortOrder
    phone?: SortOrderInput | SortOrder
    email?: SortOrderInput | SortOrder
    relationshipType?: SortOrder
    lastParticipationDate?: SortOrderInput | SortOrder
    familyId?: SortOrder
    _count?: ParentCountOrderByAggregateInput
    _max?: ParentMaxOrderByAggregateInput
    _min?: ParentMinOrderByAggregateInput
  }

  export type ParentScalarWhereWithAggregatesInput = {
    AND?: ParentScalarWhereWithAggregatesInput | ParentScalarWhereWithAggregatesInput[]
    OR?: ParentScalarWhereWithAggregatesInput[]
    NOT?: ParentScalarWhereWithAggregatesInput | ParentScalarWhereWithAggregatesInput[]
    id?: StringWithAggregatesFilter<"Parent"> | string
    name?: StringWithAggregatesFilter<"Parent"> | string
    phone?: StringNullableWithAggregatesFilter<"Parent"> | string | null
    email?: StringNullableWithAggregatesFilter<"Parent"> | string | null
    relationshipType?: StringWithAggregatesFilter<"Parent"> | string
    lastParticipationDate?: DateTimeNullableWithAggregatesFilter<"Parent"> | Date | string | null
    familyId?: StringWithAggregatesFilter<"Parent"> | string
  }

  export type ChildWhereInput = {
    AND?: ChildWhereInput | ChildWhereInput[]
    OR?: ChildWhereInput[]
    NOT?: ChildWhereInput | ChildWhereInput[]
    id?: StringFilter<"Child"> | string
    firstName?: StringFilter<"Child"> | string
    lastName?: StringFilter<"Child"> | string
    birthdate?: DateTimeFilter<"Child"> | Date | string
    allergies?: StringNullableFilter<"Child"> | string | null
    notes?: StringNullableFilter<"Child"> | string | null
    qrToken?: StringNullableFilter<"Child"> | string | null
    lastParticipationDate?: DateTimeNullableFilter<"Child"> | Date | string | null
    familyId?: StringFilter<"Child"> | string
    family?: XOR<FamilyScalarRelationFilter, FamilyWhereInput>
    checkInRecords?: CheckInRecordListRelationFilter
    tickets?: TicketListRelationFilter
  }

  export type ChildOrderByWithRelationInput = {
    id?: SortOrder
    firstName?: SortOrder
    lastName?: SortOrder
    birthdate?: SortOrder
    allergies?: SortOrderInput | SortOrder
    notes?: SortOrderInput | SortOrder
    qrToken?: SortOrderInput | SortOrder
    lastParticipationDate?: SortOrderInput | SortOrder
    familyId?: SortOrder
    family?: FamilyOrderByWithRelationInput
    checkInRecords?: CheckInRecordOrderByRelationAggregateInput
    tickets?: TicketOrderByRelationAggregateInput
  }

  export type ChildWhereUniqueInput = Prisma.AtLeast<{
    id?: string
    qrToken?: string
    AND?: ChildWhereInput | ChildWhereInput[]
    OR?: ChildWhereInput[]
    NOT?: ChildWhereInput | ChildWhereInput[]
    firstName?: StringFilter<"Child"> | string
    lastName?: StringFilter<"Child"> | string
    birthdate?: DateTimeFilter<"Child"> | Date | string
    allergies?: StringNullableFilter<"Child"> | string | null
    notes?: StringNullableFilter<"Child"> | string | null
    lastParticipationDate?: DateTimeNullableFilter<"Child"> | Date | string | null
    familyId?: StringFilter<"Child"> | string
    family?: XOR<FamilyScalarRelationFilter, FamilyWhereInput>
    checkInRecords?: CheckInRecordListRelationFilter
    tickets?: TicketListRelationFilter
  }, "id" | "qrToken">

  export type ChildOrderByWithAggregationInput = {
    id?: SortOrder
    firstName?: SortOrder
    lastName?: SortOrder
    birthdate?: SortOrder
    allergies?: SortOrderInput | SortOrder
    notes?: SortOrderInput | SortOrder
    qrToken?: SortOrderInput | SortOrder
    lastParticipationDate?: SortOrderInput | SortOrder
    familyId?: SortOrder
    _count?: ChildCountOrderByAggregateInput
    _max?: ChildMaxOrderByAggregateInput
    _min?: ChildMinOrderByAggregateInput
  }

  export type ChildScalarWhereWithAggregatesInput = {
    AND?: ChildScalarWhereWithAggregatesInput | ChildScalarWhereWithAggregatesInput[]
    OR?: ChildScalarWhereWithAggregatesInput[]
    NOT?: ChildScalarWhereWithAggregatesInput | ChildScalarWhereWithAggregatesInput[]
    id?: StringWithAggregatesFilter<"Child"> | string
    firstName?: StringWithAggregatesFilter<"Child"> | string
    lastName?: StringWithAggregatesFilter<"Child"> | string
    birthdate?: DateTimeWithAggregatesFilter<"Child"> | Date | string
    allergies?: StringNullableWithAggregatesFilter<"Child"> | string | null
    notes?: StringNullableWithAggregatesFilter<"Child"> | string | null
    qrToken?: StringNullableWithAggregatesFilter<"Child"> | string | null
    lastParticipationDate?: DateTimeNullableWithAggregatesFilter<"Child"> | Date | string | null
    familyId?: StringWithAggregatesFilter<"Child"> | string
  }

  export type EventWhereInput = {
    AND?: EventWhereInput | EventWhereInput[]
    OR?: EventWhereInput[]
    NOT?: EventWhereInput | EventWhereInput[]
    id?: StringFilter<"Event"> | string
    name?: StringFilter<"Event"> | string
    startDate?: DateTimeFilter<"Event"> | Date | string
    endDate?: DateTimeFilter<"Event"> | Date | string
    sessions?: SessionListRelationFilter
  }

  export type EventOrderByWithRelationInput = {
    id?: SortOrder
    name?: SortOrder
    startDate?: SortOrder
    endDate?: SortOrder
    sessions?: SessionOrderByRelationAggregateInput
  }

  export type EventWhereUniqueInput = Prisma.AtLeast<{
    id?: string
    AND?: EventWhereInput | EventWhereInput[]
    OR?: EventWhereInput[]
    NOT?: EventWhereInput | EventWhereInput[]
    name?: StringFilter<"Event"> | string
    startDate?: DateTimeFilter<"Event"> | Date | string
    endDate?: DateTimeFilter<"Event"> | Date | string
    sessions?: SessionListRelationFilter
  }, "id">

  export type EventOrderByWithAggregationInput = {
    id?: SortOrder
    name?: SortOrder
    startDate?: SortOrder
    endDate?: SortOrder
    _count?: EventCountOrderByAggregateInput
    _max?: EventMaxOrderByAggregateInput
    _min?: EventMinOrderByAggregateInput
  }

  export type EventScalarWhereWithAggregatesInput = {
    AND?: EventScalarWhereWithAggregatesInput | EventScalarWhereWithAggregatesInput[]
    OR?: EventScalarWhereWithAggregatesInput[]
    NOT?: EventScalarWhereWithAggregatesInput | EventScalarWhereWithAggregatesInput[]
    id?: StringWithAggregatesFilter<"Event"> | string
    name?: StringWithAggregatesFilter<"Event"> | string
    startDate?: DateTimeWithAggregatesFilter<"Event"> | Date | string
    endDate?: DateTimeWithAggregatesFilter<"Event"> | Date | string
  }

  export type SessionWhereInput = {
    AND?: SessionWhereInput | SessionWhereInput[]
    OR?: SessionWhereInput[]
    NOT?: SessionWhereInput | SessionWhereInput[]
    id?: StringFilter<"Session"> | string
    name?: StringFilter<"Session"> | string
    startTime?: DateTimeFilter<"Session"> | Date | string
    endTime?: DateTimeFilter<"Session"> | Date | string
    isActive?: BoolFilter<"Session"> | boolean
    requiresTicket?: BoolFilter<"Session"> | boolean
    eventId?: StringFilter<"Session"> | string
    event?: XOR<EventScalarRelationFilter, EventWhereInput>
    checkInRecords?: CheckInRecordListRelationFilter
    tickets?: TicketListRelationFilter
  }

  export type SessionOrderByWithRelationInput = {
    id?: SortOrder
    name?: SortOrder
    startTime?: SortOrder
    endTime?: SortOrder
    isActive?: SortOrder
    requiresTicket?: SortOrder
    eventId?: SortOrder
    event?: EventOrderByWithRelationInput
    checkInRecords?: CheckInRecordOrderByRelationAggregateInput
    tickets?: TicketOrderByRelationAggregateInput
  }

  export type SessionWhereUniqueInput = Prisma.AtLeast<{
    id?: string
    AND?: SessionWhereInput | SessionWhereInput[]
    OR?: SessionWhereInput[]
    NOT?: SessionWhereInput | SessionWhereInput[]
    name?: StringFilter<"Session"> | string
    startTime?: DateTimeFilter<"Session"> | Date | string
    endTime?: DateTimeFilter<"Session"> | Date | string
    isActive?: BoolFilter<"Session"> | boolean
    requiresTicket?: BoolFilter<"Session"> | boolean
    eventId?: StringFilter<"Session"> | string
    event?: XOR<EventScalarRelationFilter, EventWhereInput>
    checkInRecords?: CheckInRecordListRelationFilter
    tickets?: TicketListRelationFilter
  }, "id">

  export type SessionOrderByWithAggregationInput = {
    id?: SortOrder
    name?: SortOrder
    startTime?: SortOrder
    endTime?: SortOrder
    isActive?: SortOrder
    requiresTicket?: SortOrder
    eventId?: SortOrder
    _count?: SessionCountOrderByAggregateInput
    _max?: SessionMaxOrderByAggregateInput
    _min?: SessionMinOrderByAggregateInput
  }

  export type SessionScalarWhereWithAggregatesInput = {
    AND?: SessionScalarWhereWithAggregatesInput | SessionScalarWhereWithAggregatesInput[]
    OR?: SessionScalarWhereWithAggregatesInput[]
    NOT?: SessionScalarWhereWithAggregatesInput | SessionScalarWhereWithAggregatesInput[]
    id?: StringWithAggregatesFilter<"Session"> | string
    name?: StringWithAggregatesFilter<"Session"> | string
    startTime?: DateTimeWithAggregatesFilter<"Session"> | Date | string
    endTime?: DateTimeWithAggregatesFilter<"Session"> | Date | string
    isActive?: BoolWithAggregatesFilter<"Session"> | boolean
    requiresTicket?: BoolWithAggregatesFilter<"Session"> | boolean
    eventId?: StringWithAggregatesFilter<"Session"> | string
  }

  export type TicketWhereInput = {
    AND?: TicketWhereInput | TicketWhereInput[]
    OR?: TicketWhereInput[]
    NOT?: TicketWhereInput | TicketWhereInput[]
    id?: StringFilter<"Ticket"> | string
    type?: StringFilter<"Ticket"> | string
    childId?: StringFilter<"Ticket"> | string
    sessionId?: StringNullableFilter<"Ticket"> | string | null
    child?: XOR<ChildScalarRelationFilter, ChildWhereInput>
    session?: XOR<SessionNullableScalarRelationFilter, SessionWhereInput> | null
  }

  export type TicketOrderByWithRelationInput = {
    id?: SortOrder
    type?: SortOrder
    childId?: SortOrder
    sessionId?: SortOrderInput | SortOrder
    child?: ChildOrderByWithRelationInput
    session?: SessionOrderByWithRelationInput
  }

  export type TicketWhereUniqueInput = Prisma.AtLeast<{
    id?: string
    AND?: TicketWhereInput | TicketWhereInput[]
    OR?: TicketWhereInput[]
    NOT?: TicketWhereInput | TicketWhereInput[]
    type?: StringFilter<"Ticket"> | string
    childId?: StringFilter<"Ticket"> | string
    sessionId?: StringNullableFilter<"Ticket"> | string | null
    child?: XOR<ChildScalarRelationFilter, ChildWhereInput>
    session?: XOR<SessionNullableScalarRelationFilter, SessionWhereInput> | null
  }, "id">

  export type TicketOrderByWithAggregationInput = {
    id?: SortOrder
    type?: SortOrder
    childId?: SortOrder
    sessionId?: SortOrderInput | SortOrder
    _count?: TicketCountOrderByAggregateInput
    _max?: TicketMaxOrderByAggregateInput
    _min?: TicketMinOrderByAggregateInput
  }

  export type TicketScalarWhereWithAggregatesInput = {
    AND?: TicketScalarWhereWithAggregatesInput | TicketScalarWhereWithAggregatesInput[]
    OR?: TicketScalarWhereWithAggregatesInput[]
    NOT?: TicketScalarWhereWithAggregatesInput | TicketScalarWhereWithAggregatesInput[]
    id?: StringWithAggregatesFilter<"Ticket"> | string
    type?: StringWithAggregatesFilter<"Ticket"> | string
    childId?: StringWithAggregatesFilter<"Ticket"> | string
    sessionId?: StringNullableWithAggregatesFilter<"Ticket"> | string | null
  }

  export type CheckInRecordWhereInput = {
    AND?: CheckInRecordWhereInput | CheckInRecordWhereInput[]
    OR?: CheckInRecordWhereInput[]
    NOT?: CheckInRecordWhereInput | CheckInRecordWhereInput[]
    id?: StringFilter<"CheckInRecord"> | string
    checkInTime?: DateTimeFilter<"CheckInRecord"> | Date | string
    checkOutTime?: DateTimeNullableFilter<"CheckInRecord"> | Date | string | null
    pickedUpBy?: StringNullableFilter<"CheckInRecord"> | string | null
    childId?: StringFilter<"CheckInRecord"> | string
    sessionId?: StringFilter<"CheckInRecord"> | string
    checkInStaffId?: StringFilter<"CheckInRecord"> | string
    checkOutStaffId?: StringNullableFilter<"CheckInRecord"> | string | null
    child?: XOR<ChildScalarRelationFilter, ChildWhereInput>
    session?: XOR<SessionScalarRelationFilter, SessionWhereInput>
    checkInStaff?: XOR<AdminUserScalarRelationFilter, AdminUserWhereInput>
    checkOutStaff?: XOR<AdminUserNullableScalarRelationFilter, AdminUserWhereInput> | null
  }

  export type CheckInRecordOrderByWithRelationInput = {
    id?: SortOrder
    checkInTime?: SortOrder
    checkOutTime?: SortOrderInput | SortOrder
    pickedUpBy?: SortOrderInput | SortOrder
    childId?: SortOrder
    sessionId?: SortOrder
    checkInStaffId?: SortOrder
    checkOutStaffId?: SortOrderInput | SortOrder
    child?: ChildOrderByWithRelationInput
    session?: SessionOrderByWithRelationInput
    checkInStaff?: AdminUserOrderByWithRelationInput
    checkOutStaff?: AdminUserOrderByWithRelationInput
  }

  export type CheckInRecordWhereUniqueInput = Prisma.AtLeast<{
    id?: string
    childId_sessionId_checkInTime?: CheckInRecordChildIdSessionIdCheckInTimeCompoundUniqueInput
    AND?: CheckInRecordWhereInput | CheckInRecordWhereInput[]
    OR?: CheckInRecordWhereInput[]
    NOT?: CheckInRecordWhereInput | CheckInRecordWhereInput[]
    checkInTime?: DateTimeFilter<"CheckInRecord"> | Date | string
    checkOutTime?: DateTimeNullableFilter<"CheckInRecord"> | Date | string | null
    pickedUpBy?: StringNullableFilter<"CheckInRecord"> | string | null
    childId?: StringFilter<"CheckInRecord"> | string
    sessionId?: StringFilter<"CheckInRecord"> | string
    checkInStaffId?: StringFilter<"CheckInRecord"> | string
    checkOutStaffId?: StringNullableFilter<"CheckInRecord"> | string | null
    child?: XOR<ChildScalarRelationFilter, ChildWhereInput>
    session?: XOR<SessionScalarRelationFilter, SessionWhereInput>
    checkInStaff?: XOR<AdminUserScalarRelationFilter, AdminUserWhereInput>
    checkOutStaff?: XOR<AdminUserNullableScalarRelationFilter, AdminUserWhereInput> | null
  }, "id" | "childId_sessionId_checkInTime">

  export type CheckInRecordOrderByWithAggregationInput = {
    id?: SortOrder
    checkInTime?: SortOrder
    checkOutTime?: SortOrderInput | SortOrder
    pickedUpBy?: SortOrderInput | SortOrder
    childId?: SortOrder
    sessionId?: SortOrder
    checkInStaffId?: SortOrder
    checkOutStaffId?: SortOrderInput | SortOrder
    _count?: CheckInRecordCountOrderByAggregateInput
    _max?: CheckInRecordMaxOrderByAggregateInput
    _min?: CheckInRecordMinOrderByAggregateInput
  }

  export type CheckInRecordScalarWhereWithAggregatesInput = {
    AND?: CheckInRecordScalarWhereWithAggregatesInput | CheckInRecordScalarWhereWithAggregatesInput[]
    OR?: CheckInRecordScalarWhereWithAggregatesInput[]
    NOT?: CheckInRecordScalarWhereWithAggregatesInput | CheckInRecordScalarWhereWithAggregatesInput[]
    id?: StringWithAggregatesFilter<"CheckInRecord"> | string
    checkInTime?: DateTimeWithAggregatesFilter<"CheckInRecord"> | Date | string
    checkOutTime?: DateTimeNullableWithAggregatesFilter<"CheckInRecord"> | Date | string | null
    pickedUpBy?: StringNullableWithAggregatesFilter<"CheckInRecord"> | string | null
    childId?: StringWithAggregatesFilter<"CheckInRecord"> | string
    sessionId?: StringWithAggregatesFilter<"CheckInRecord"> | string
    checkInStaffId?: StringWithAggregatesFilter<"CheckInRecord"> | string
    checkOutStaffId?: StringNullableWithAggregatesFilter<"CheckInRecord"> | string | null
  }

  export type AuditLogWhereInput = {
    AND?: AuditLogWhereInput | AuditLogWhereInput[]
    OR?: AuditLogWhereInput[]
    NOT?: AuditLogWhereInput | AuditLogWhereInput[]
    id?: StringFilter<"AuditLog"> | string
    timestamp?: DateTimeFilter<"AuditLog"> | Date | string
    userId?: StringFilter<"AuditLog"> | string
    action?: StringFilter<"AuditLog"> | string
    entityType?: StringFilter<"AuditLog"> | string
    entityId?: StringFilter<"AuditLog"> | string
    details?: JsonNullableFilter<"AuditLog">
  }

  export type AuditLogOrderByWithRelationInput = {
    id?: SortOrder
    timestamp?: SortOrder
    userId?: SortOrder
    action?: SortOrder
    entityType?: SortOrder
    entityId?: SortOrder
    details?: SortOrderInput | SortOrder
  }

  export type AuditLogWhereUniqueInput = Prisma.AtLeast<{
    id?: string
    AND?: AuditLogWhereInput | AuditLogWhereInput[]
    OR?: AuditLogWhereInput[]
    NOT?: AuditLogWhereInput | AuditLogWhereInput[]
    timestamp?: DateTimeFilter<"AuditLog"> | Date | string
    userId?: StringFilter<"AuditLog"> | string
    action?: StringFilter<"AuditLog"> | string
    entityType?: StringFilter<"AuditLog"> | string
    entityId?: StringFilter<"AuditLog"> | string
    details?: JsonNullableFilter<"AuditLog">
  }, "id">

  export type AuditLogOrderByWithAggregationInput = {
    id?: SortOrder
    timestamp?: SortOrder
    userId?: SortOrder
    action?: SortOrder
    entityType?: SortOrder
    entityId?: SortOrder
    details?: SortOrderInput | SortOrder
    _count?: AuditLogCountOrderByAggregateInput
    _max?: AuditLogMaxOrderByAggregateInput
    _min?: AuditLogMinOrderByAggregateInput
  }

  export type AuditLogScalarWhereWithAggregatesInput = {
    AND?: AuditLogScalarWhereWithAggregatesInput | AuditLogScalarWhereWithAggregatesInput[]
    OR?: AuditLogScalarWhereWithAggregatesInput[]
    NOT?: AuditLogScalarWhereWithAggregatesInput | AuditLogScalarWhereWithAggregatesInput[]
    id?: StringWithAggregatesFilter<"AuditLog"> | string
    timestamp?: DateTimeWithAggregatesFilter<"AuditLog"> | Date | string
    userId?: StringWithAggregatesFilter<"AuditLog"> | string
    action?: StringWithAggregatesFilter<"AuditLog"> | string
    entityType?: StringWithAggregatesFilter<"AuditLog"> | string
    entityId?: StringWithAggregatesFilter<"AuditLog"> | string
    details?: JsonNullableWithAggregatesFilter<"AuditLog">
  }

  export type AdminUserCreateInput = {
    id?: string
    username: string
    passwordHash: string
    name: string
    createdAt?: Date | string
    lastLogin?: Date | string | null
    isActive?: boolean
    checkInsPerformed?: CheckInRecordCreateNestedManyWithoutCheckInStaffInput
    checkOutsPerformed?: CheckInRecordCreateNestedManyWithoutCheckOutStaffInput
  }

  export type AdminUserUncheckedCreateInput = {
    id?: string
    username: string
    passwordHash: string
    name: string
    createdAt?: Date | string
    lastLogin?: Date | string | null
    isActive?: boolean
    checkInsPerformed?: CheckInRecordUncheckedCreateNestedManyWithoutCheckInStaffInput
    checkOutsPerformed?: CheckInRecordUncheckedCreateNestedManyWithoutCheckOutStaffInput
  }

  export type AdminUserUpdateInput = {
    id?: StringFieldUpdateOperationsInput | string
    username?: StringFieldUpdateOperationsInput | string
    passwordHash?: StringFieldUpdateOperationsInput | string
    name?: StringFieldUpdateOperationsInput | string
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
    lastLogin?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    isActive?: BoolFieldUpdateOperationsInput | boolean
    checkInsPerformed?: CheckInRecordUpdateManyWithoutCheckInStaffNestedInput
    checkOutsPerformed?: CheckInRecordUpdateManyWithoutCheckOutStaffNestedInput
  }

  export type AdminUserUncheckedUpdateInput = {
    id?: StringFieldUpdateOperationsInput | string
    username?: StringFieldUpdateOperationsInput | string
    passwordHash?: StringFieldUpdateOperationsInput | string
    name?: StringFieldUpdateOperationsInput | string
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
    lastLogin?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    isActive?: BoolFieldUpdateOperationsInput | boolean
    checkInsPerformed?: CheckInRecordUncheckedUpdateManyWithoutCheckInStaffNestedInput
    checkOutsPerformed?: CheckInRecordUncheckedUpdateManyWithoutCheckOutStaffNestedInput
  }

  export type AdminUserCreateManyInput = {
    id?: string
    username: string
    passwordHash: string
    name: string
    createdAt?: Date | string
    lastLogin?: Date | string | null
    isActive?: boolean
  }

  export type AdminUserUpdateManyMutationInput = {
    id?: StringFieldUpdateOperationsInput | string
    username?: StringFieldUpdateOperationsInput | string
    passwordHash?: StringFieldUpdateOperationsInput | string
    name?: StringFieldUpdateOperationsInput | string
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
    lastLogin?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    isActive?: BoolFieldUpdateOperationsInput | boolean
  }

  export type AdminUserUncheckedUpdateManyInput = {
    id?: StringFieldUpdateOperationsInput | string
    username?: StringFieldUpdateOperationsInput | string
    passwordHash?: StringFieldUpdateOperationsInput | string
    name?: StringFieldUpdateOperationsInput | string
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
    lastLogin?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    isActive?: BoolFieldUpdateOperationsInput | boolean
  }

  export type FamilyCreateInput = {
    id?: string
    lastParticipationDate?: Date | string | null
    parents?: ParentCreateNestedManyWithoutFamilyInput
    children?: ChildCreateNestedManyWithoutFamilyInput
  }

  export type FamilyUncheckedCreateInput = {
    id?: string
    lastParticipationDate?: Date | string | null
    parents?: ParentUncheckedCreateNestedManyWithoutFamilyInput
    children?: ChildUncheckedCreateNestedManyWithoutFamilyInput
  }

  export type FamilyUpdateInput = {
    id?: StringFieldUpdateOperationsInput | string
    lastParticipationDate?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    parents?: ParentUpdateManyWithoutFamilyNestedInput
    children?: ChildUpdateManyWithoutFamilyNestedInput
  }

  export type FamilyUncheckedUpdateInput = {
    id?: StringFieldUpdateOperationsInput | string
    lastParticipationDate?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    parents?: ParentUncheckedUpdateManyWithoutFamilyNestedInput
    children?: ChildUncheckedUpdateManyWithoutFamilyNestedInput
  }

  export type FamilyCreateManyInput = {
    id?: string
    lastParticipationDate?: Date | string | null
  }

  export type FamilyUpdateManyMutationInput = {
    id?: StringFieldUpdateOperationsInput | string
    lastParticipationDate?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
  }

  export type FamilyUncheckedUpdateManyInput = {
    id?: StringFieldUpdateOperationsInput | string
    lastParticipationDate?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
  }

  export type ParentCreateInput = {
    id?: string
    name: string
    phone?: string | null
    email?: string | null
    relationshipType: string
    lastParticipationDate?: Date | string | null
    family: FamilyCreateNestedOneWithoutParentsInput
  }

  export type ParentUncheckedCreateInput = {
    id?: string
    name: string
    phone?: string | null
    email?: string | null
    relationshipType: string
    lastParticipationDate?: Date | string | null
    familyId: string
  }

  export type ParentUpdateInput = {
    id?: StringFieldUpdateOperationsInput | string
    name?: StringFieldUpdateOperationsInput | string
    phone?: NullableStringFieldUpdateOperationsInput | string | null
    email?: NullableStringFieldUpdateOperationsInput | string | null
    relationshipType?: StringFieldUpdateOperationsInput | string
    lastParticipationDate?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    family?: FamilyUpdateOneRequiredWithoutParentsNestedInput
  }

  export type ParentUncheckedUpdateInput = {
    id?: StringFieldUpdateOperationsInput | string
    name?: StringFieldUpdateOperationsInput | string
    phone?: NullableStringFieldUpdateOperationsInput | string | null
    email?: NullableStringFieldUpdateOperationsInput | string | null
    relationshipType?: StringFieldUpdateOperationsInput | string
    lastParticipationDate?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    familyId?: StringFieldUpdateOperationsInput | string
  }

  export type ParentCreateManyInput = {
    id?: string
    name: string
    phone?: string | null
    email?: string | null
    relationshipType: string
    lastParticipationDate?: Date | string | null
    familyId: string
  }

  export type ParentUpdateManyMutationInput = {
    id?: StringFieldUpdateOperationsInput | string
    name?: StringFieldUpdateOperationsInput | string
    phone?: NullableStringFieldUpdateOperationsInput | string | null
    email?: NullableStringFieldUpdateOperationsInput | string | null
    relationshipType?: StringFieldUpdateOperationsInput | string
    lastParticipationDate?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
  }

  export type ParentUncheckedUpdateManyInput = {
    id?: StringFieldUpdateOperationsInput | string
    name?: StringFieldUpdateOperationsInput | string
    phone?: NullableStringFieldUpdateOperationsInput | string | null
    email?: NullableStringFieldUpdateOperationsInput | string | null
    relationshipType?: StringFieldUpdateOperationsInput | string
    lastParticipationDate?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    familyId?: StringFieldUpdateOperationsInput | string
  }

  export type ChildCreateInput = {
    id?: string
    firstName: string
    lastName: string
    birthdate: Date | string
    allergies?: string | null
    notes?: string | null
    qrToken?: string | null
    lastParticipationDate?: Date | string | null
    family: FamilyCreateNestedOneWithoutChildrenInput
    checkInRecords?: CheckInRecordCreateNestedManyWithoutChildInput
    tickets?: TicketCreateNestedManyWithoutChildInput
  }

  export type ChildUncheckedCreateInput = {
    id?: string
    firstName: string
    lastName: string
    birthdate: Date | string
    allergies?: string | null
    notes?: string | null
    qrToken?: string | null
    lastParticipationDate?: Date | string | null
    familyId: string
    checkInRecords?: CheckInRecordUncheckedCreateNestedManyWithoutChildInput
    tickets?: TicketUncheckedCreateNestedManyWithoutChildInput
  }

  export type ChildUpdateInput = {
    id?: StringFieldUpdateOperationsInput | string
    firstName?: StringFieldUpdateOperationsInput | string
    lastName?: StringFieldUpdateOperationsInput | string
    birthdate?: DateTimeFieldUpdateOperationsInput | Date | string
    allergies?: NullableStringFieldUpdateOperationsInput | string | null
    notes?: NullableStringFieldUpdateOperationsInput | string | null
    qrToken?: NullableStringFieldUpdateOperationsInput | string | null
    lastParticipationDate?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    family?: FamilyUpdateOneRequiredWithoutChildrenNestedInput
    checkInRecords?: CheckInRecordUpdateManyWithoutChildNestedInput
    tickets?: TicketUpdateManyWithoutChildNestedInput
  }

  export type ChildUncheckedUpdateInput = {
    id?: StringFieldUpdateOperationsInput | string
    firstName?: StringFieldUpdateOperationsInput | string
    lastName?: StringFieldUpdateOperationsInput | string
    birthdate?: DateTimeFieldUpdateOperationsInput | Date | string
    allergies?: NullableStringFieldUpdateOperationsInput | string | null
    notes?: NullableStringFieldUpdateOperationsInput | string | null
    qrToken?: NullableStringFieldUpdateOperationsInput | string | null
    lastParticipationDate?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    familyId?: StringFieldUpdateOperationsInput | string
    checkInRecords?: CheckInRecordUncheckedUpdateManyWithoutChildNestedInput
    tickets?: TicketUncheckedUpdateManyWithoutChildNestedInput
  }

  export type ChildCreateManyInput = {
    id?: string
    firstName: string
    lastName: string
    birthdate: Date | string
    allergies?: string | null
    notes?: string | null
    qrToken?: string | null
    lastParticipationDate?: Date | string | null
    familyId: string
  }

  export type ChildUpdateManyMutationInput = {
    id?: StringFieldUpdateOperationsInput | string
    firstName?: StringFieldUpdateOperationsInput | string
    lastName?: StringFieldUpdateOperationsInput | string
    birthdate?: DateTimeFieldUpdateOperationsInput | Date | string
    allergies?: NullableStringFieldUpdateOperationsInput | string | null
    notes?: NullableStringFieldUpdateOperationsInput | string | null
    qrToken?: NullableStringFieldUpdateOperationsInput | string | null
    lastParticipationDate?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
  }

  export type ChildUncheckedUpdateManyInput = {
    id?: StringFieldUpdateOperationsInput | string
    firstName?: StringFieldUpdateOperationsInput | string
    lastName?: StringFieldUpdateOperationsInput | string
    birthdate?: DateTimeFieldUpdateOperationsInput | Date | string
    allergies?: NullableStringFieldUpdateOperationsInput | string | null
    notes?: NullableStringFieldUpdateOperationsInput | string | null
    qrToken?: NullableStringFieldUpdateOperationsInput | string | null
    lastParticipationDate?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    familyId?: StringFieldUpdateOperationsInput | string
  }

  export type EventCreateInput = {
    id?: string
    name: string
    startDate: Date | string
    endDate: Date | string
    sessions?: SessionCreateNestedManyWithoutEventInput
  }

  export type EventUncheckedCreateInput = {
    id?: string
    name: string
    startDate: Date | string
    endDate: Date | string
    sessions?: SessionUncheckedCreateNestedManyWithoutEventInput
  }

  export type EventUpdateInput = {
    id?: StringFieldUpdateOperationsInput | string
    name?: StringFieldUpdateOperationsInput | string
    startDate?: DateTimeFieldUpdateOperationsInput | Date | string
    endDate?: DateTimeFieldUpdateOperationsInput | Date | string
    sessions?: SessionUpdateManyWithoutEventNestedInput
  }

  export type EventUncheckedUpdateInput = {
    id?: StringFieldUpdateOperationsInput | string
    name?: StringFieldUpdateOperationsInput | string
    startDate?: DateTimeFieldUpdateOperationsInput | Date | string
    endDate?: DateTimeFieldUpdateOperationsInput | Date | string
    sessions?: SessionUncheckedUpdateManyWithoutEventNestedInput
  }

  export type EventCreateManyInput = {
    id?: string
    name: string
    startDate: Date | string
    endDate: Date | string
  }

  export type EventUpdateManyMutationInput = {
    id?: StringFieldUpdateOperationsInput | string
    name?: StringFieldUpdateOperationsInput | string
    startDate?: DateTimeFieldUpdateOperationsInput | Date | string
    endDate?: DateTimeFieldUpdateOperationsInput | Date | string
  }

  export type EventUncheckedUpdateManyInput = {
    id?: StringFieldUpdateOperationsInput | string
    name?: StringFieldUpdateOperationsInput | string
    startDate?: DateTimeFieldUpdateOperationsInput | Date | string
    endDate?: DateTimeFieldUpdateOperationsInput | Date | string
  }

  export type SessionCreateInput = {
    id?: string
    name: string
    startTime: Date | string
    endTime: Date | string
    isActive?: boolean
    requiresTicket?: boolean
    event: EventCreateNestedOneWithoutSessionsInput
    checkInRecords?: CheckInRecordCreateNestedManyWithoutSessionInput
    tickets?: TicketCreateNestedManyWithoutSessionInput
  }

  export type SessionUncheckedCreateInput = {
    id?: string
    name: string
    startTime: Date | string
    endTime: Date | string
    isActive?: boolean
    requiresTicket?: boolean
    eventId: string
    checkInRecords?: CheckInRecordUncheckedCreateNestedManyWithoutSessionInput
    tickets?: TicketUncheckedCreateNestedManyWithoutSessionInput
  }

  export type SessionUpdateInput = {
    id?: StringFieldUpdateOperationsInput | string
    name?: StringFieldUpdateOperationsInput | string
    startTime?: DateTimeFieldUpdateOperationsInput | Date | string
    endTime?: DateTimeFieldUpdateOperationsInput | Date | string
    isActive?: BoolFieldUpdateOperationsInput | boolean
    requiresTicket?: BoolFieldUpdateOperationsInput | boolean
    event?: EventUpdateOneRequiredWithoutSessionsNestedInput
    checkInRecords?: CheckInRecordUpdateManyWithoutSessionNestedInput
    tickets?: TicketUpdateManyWithoutSessionNestedInput
  }

  export type SessionUncheckedUpdateInput = {
    id?: StringFieldUpdateOperationsInput | string
    name?: StringFieldUpdateOperationsInput | string
    startTime?: DateTimeFieldUpdateOperationsInput | Date | string
    endTime?: DateTimeFieldUpdateOperationsInput | Date | string
    isActive?: BoolFieldUpdateOperationsInput | boolean
    requiresTicket?: BoolFieldUpdateOperationsInput | boolean
    eventId?: StringFieldUpdateOperationsInput | string
    checkInRecords?: CheckInRecordUncheckedUpdateManyWithoutSessionNestedInput
    tickets?: TicketUncheckedUpdateManyWithoutSessionNestedInput
  }

  export type SessionCreateManyInput = {
    id?: string
    name: string
    startTime: Date | string
    endTime: Date | string
    isActive?: boolean
    requiresTicket?: boolean
    eventId: string
  }

  export type SessionUpdateManyMutationInput = {
    id?: StringFieldUpdateOperationsInput | string
    name?: StringFieldUpdateOperationsInput | string
    startTime?: DateTimeFieldUpdateOperationsInput | Date | string
    endTime?: DateTimeFieldUpdateOperationsInput | Date | string
    isActive?: BoolFieldUpdateOperationsInput | boolean
    requiresTicket?: BoolFieldUpdateOperationsInput | boolean
  }

  export type SessionUncheckedUpdateManyInput = {
    id?: StringFieldUpdateOperationsInput | string
    name?: StringFieldUpdateOperationsInput | string
    startTime?: DateTimeFieldUpdateOperationsInput | Date | string
    endTime?: DateTimeFieldUpdateOperationsInput | Date | string
    isActive?: BoolFieldUpdateOperationsInput | boolean
    requiresTicket?: BoolFieldUpdateOperationsInput | boolean
    eventId?: StringFieldUpdateOperationsInput | string
  }

  export type TicketCreateInput = {
    id?: string
    type: string
    child: ChildCreateNestedOneWithoutTicketsInput
    session?: SessionCreateNestedOneWithoutTicketsInput
  }

  export type TicketUncheckedCreateInput = {
    id?: string
    type: string
    childId: string
    sessionId?: string | null
  }

  export type TicketUpdateInput = {
    id?: StringFieldUpdateOperationsInput | string
    type?: StringFieldUpdateOperationsInput | string
    child?: ChildUpdateOneRequiredWithoutTicketsNestedInput
    session?: SessionUpdateOneWithoutTicketsNestedInput
  }

  export type TicketUncheckedUpdateInput = {
    id?: StringFieldUpdateOperationsInput | string
    type?: StringFieldUpdateOperationsInput | string
    childId?: StringFieldUpdateOperationsInput | string
    sessionId?: NullableStringFieldUpdateOperationsInput | string | null
  }

  export type TicketCreateManyInput = {
    id?: string
    type: string
    childId: string
    sessionId?: string | null
  }

  export type TicketUpdateManyMutationInput = {
    id?: StringFieldUpdateOperationsInput | string
    type?: StringFieldUpdateOperationsInput | string
  }

  export type TicketUncheckedUpdateManyInput = {
    id?: StringFieldUpdateOperationsInput | string
    type?: StringFieldUpdateOperationsInput | string
    childId?: StringFieldUpdateOperationsInput | string
    sessionId?: NullableStringFieldUpdateOperationsInput | string | null
  }

  export type CheckInRecordCreateInput = {
    id?: string
    checkInTime?: Date | string
    checkOutTime?: Date | string | null
    pickedUpBy?: string | null
    child: ChildCreateNestedOneWithoutCheckInRecordsInput
    session: SessionCreateNestedOneWithoutCheckInRecordsInput
    checkInStaff: AdminUserCreateNestedOneWithoutCheckInsPerformedInput
    checkOutStaff?: AdminUserCreateNestedOneWithoutCheckOutsPerformedInput
  }

  export type CheckInRecordUncheckedCreateInput = {
    id?: string
    checkInTime?: Date | string
    checkOutTime?: Date | string | null
    pickedUpBy?: string | null
    childId: string
    sessionId: string
    checkInStaffId: string
    checkOutStaffId?: string | null
  }

  export type CheckInRecordUpdateInput = {
    id?: StringFieldUpdateOperationsInput | string
    checkInTime?: DateTimeFieldUpdateOperationsInput | Date | string
    checkOutTime?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    pickedUpBy?: NullableStringFieldUpdateOperationsInput | string | null
    child?: ChildUpdateOneRequiredWithoutCheckInRecordsNestedInput
    session?: SessionUpdateOneRequiredWithoutCheckInRecordsNestedInput
    checkInStaff?: AdminUserUpdateOneRequiredWithoutCheckInsPerformedNestedInput
    checkOutStaff?: AdminUserUpdateOneWithoutCheckOutsPerformedNestedInput
  }

  export type CheckInRecordUncheckedUpdateInput = {
    id?: StringFieldUpdateOperationsInput | string
    checkInTime?: DateTimeFieldUpdateOperationsInput | Date | string
    checkOutTime?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    pickedUpBy?: NullableStringFieldUpdateOperationsInput | string | null
    childId?: StringFieldUpdateOperationsInput | string
    sessionId?: StringFieldUpdateOperationsInput | string
    checkInStaffId?: StringFieldUpdateOperationsInput | string
    checkOutStaffId?: NullableStringFieldUpdateOperationsInput | string | null
  }

  export type CheckInRecordCreateManyInput = {
    id?: string
    checkInTime?: Date | string
    checkOutTime?: Date | string | null
    pickedUpBy?: string | null
    childId: string
    sessionId: string
    checkInStaffId: string
    checkOutStaffId?: string | null
  }

  export type CheckInRecordUpdateManyMutationInput = {
    id?: StringFieldUpdateOperationsInput | string
    checkInTime?: DateTimeFieldUpdateOperationsInput | Date | string
    checkOutTime?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    pickedUpBy?: NullableStringFieldUpdateOperationsInput | string | null
  }

  export type CheckInRecordUncheckedUpdateManyInput = {
    id?: StringFieldUpdateOperationsInput | string
    checkInTime?: DateTimeFieldUpdateOperationsInput | Date | string
    checkOutTime?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    pickedUpBy?: NullableStringFieldUpdateOperationsInput | string | null
    childId?: StringFieldUpdateOperationsInput | string
    sessionId?: StringFieldUpdateOperationsInput | string
    checkInStaffId?: StringFieldUpdateOperationsInput | string
    checkOutStaffId?: NullableStringFieldUpdateOperationsInput | string | null
  }

  export type AuditLogCreateInput = {
    id?: string
    timestamp?: Date | string
    userId: string
    action: string
    entityType: string
    entityId: string
    details?: NullableJsonNullValueInput | InputJsonValue
  }

  export type AuditLogUncheckedCreateInput = {
    id?: string
    timestamp?: Date | string
    userId: string
    action: string
    entityType: string
    entityId: string
    details?: NullableJsonNullValueInput | InputJsonValue
  }

  export type AuditLogUpdateInput = {
    id?: StringFieldUpdateOperationsInput | string
    timestamp?: DateTimeFieldUpdateOperationsInput | Date | string
    userId?: StringFieldUpdateOperationsInput | string
    action?: StringFieldUpdateOperationsInput | string
    entityType?: StringFieldUpdateOperationsInput | string
    entityId?: StringFieldUpdateOperationsInput | string
    details?: NullableJsonNullValueInput | InputJsonValue
  }

  export type AuditLogUncheckedUpdateInput = {
    id?: StringFieldUpdateOperationsInput | string
    timestamp?: DateTimeFieldUpdateOperationsInput | Date | string
    userId?: StringFieldUpdateOperationsInput | string
    action?: StringFieldUpdateOperationsInput | string
    entityType?: StringFieldUpdateOperationsInput | string
    entityId?: StringFieldUpdateOperationsInput | string
    details?: NullableJsonNullValueInput | InputJsonValue
  }

  export type AuditLogCreateManyInput = {
    id?: string
    timestamp?: Date | string
    userId: string
    action: string
    entityType: string
    entityId: string
    details?: NullableJsonNullValueInput | InputJsonValue
  }

  export type AuditLogUpdateManyMutationInput = {
    id?: StringFieldUpdateOperationsInput | string
    timestamp?: DateTimeFieldUpdateOperationsInput | Date | string
    userId?: StringFieldUpdateOperationsInput | string
    action?: StringFieldUpdateOperationsInput | string
    entityType?: StringFieldUpdateOperationsInput | string
    entityId?: StringFieldUpdateOperationsInput | string
    details?: NullableJsonNullValueInput | InputJsonValue
  }

  export type AuditLogUncheckedUpdateManyInput = {
    id?: StringFieldUpdateOperationsInput | string
    timestamp?: DateTimeFieldUpdateOperationsInput | Date | string
    userId?: StringFieldUpdateOperationsInput | string
    action?: StringFieldUpdateOperationsInput | string
    entityType?: StringFieldUpdateOperationsInput | string
    entityId?: StringFieldUpdateOperationsInput | string
    details?: NullableJsonNullValueInput | InputJsonValue
  }

  export type StringFilter<$PrismaModel = never> = {
    equals?: string | StringFieldRefInput<$PrismaModel>
    in?: string[] | ListStringFieldRefInput<$PrismaModel>
    notIn?: string[] | ListStringFieldRefInput<$PrismaModel>
    lt?: string | StringFieldRefInput<$PrismaModel>
    lte?: string | StringFieldRefInput<$PrismaModel>
    gt?: string | StringFieldRefInput<$PrismaModel>
    gte?: string | StringFieldRefInput<$PrismaModel>
    contains?: string | StringFieldRefInput<$PrismaModel>
    startsWith?: string | StringFieldRefInput<$PrismaModel>
    endsWith?: string | StringFieldRefInput<$PrismaModel>
    mode?: QueryMode
    not?: NestedStringFilter<$PrismaModel> | string
  }

  export type DateTimeFilter<$PrismaModel = never> = {
    equals?: Date | string | DateTimeFieldRefInput<$PrismaModel>
    in?: Date[] | string[] | ListDateTimeFieldRefInput<$PrismaModel>
    notIn?: Date[] | string[] | ListDateTimeFieldRefInput<$PrismaModel>
    lt?: Date | string | DateTimeFieldRefInput<$PrismaModel>
    lte?: Date | string | DateTimeFieldRefInput<$PrismaModel>
    gt?: Date | string | DateTimeFieldRefInput<$PrismaModel>
    gte?: Date | string | DateTimeFieldRefInput<$PrismaModel>
    not?: NestedDateTimeFilter<$PrismaModel> | Date | string
  }

  export type DateTimeNullableFilter<$PrismaModel = never> = {
    equals?: Date | string | DateTimeFieldRefInput<$PrismaModel> | null
    in?: Date[] | string[] | ListDateTimeFieldRefInput<$PrismaModel> | null
    notIn?: Date[] | string[] | ListDateTimeFieldRefInput<$PrismaModel> | null
    lt?: Date | string | DateTimeFieldRefInput<$PrismaModel>
    lte?: Date | string | DateTimeFieldRefInput<$PrismaModel>
    gt?: Date | string | DateTimeFieldRefInput<$PrismaModel>
    gte?: Date | string | DateTimeFieldRefInput<$PrismaModel>
    not?: NestedDateTimeNullableFilter<$PrismaModel> | Date | string | null
  }

  export type BoolFilter<$PrismaModel = never> = {
    equals?: boolean | BooleanFieldRefInput<$PrismaModel>
    not?: NestedBoolFilter<$PrismaModel> | boolean
  }

  export type CheckInRecordListRelationFilter = {
    every?: CheckInRecordWhereInput
    some?: CheckInRecordWhereInput
    none?: CheckInRecordWhereInput
  }

  export type SortOrderInput = {
    sort: SortOrder
    nulls?: NullsOrder
  }

  export type CheckInRecordOrderByRelationAggregateInput = {
    _count?: SortOrder
  }

  export type AdminUserCountOrderByAggregateInput = {
    id?: SortOrder
    username?: SortOrder
    passwordHash?: SortOrder
    name?: SortOrder
    createdAt?: SortOrder
    lastLogin?: SortOrder
    isActive?: SortOrder
  }

  export type AdminUserMaxOrderByAggregateInput = {
    id?: SortOrder
    username?: SortOrder
    passwordHash?: SortOrder
    name?: SortOrder
    createdAt?: SortOrder
    lastLogin?: SortOrder
    isActive?: SortOrder
  }

  export type AdminUserMinOrderByAggregateInput = {
    id?: SortOrder
    username?: SortOrder
    passwordHash?: SortOrder
    name?: SortOrder
    createdAt?: SortOrder
    lastLogin?: SortOrder
    isActive?: SortOrder
  }

  export type StringWithAggregatesFilter<$PrismaModel = never> = {
    equals?: string | StringFieldRefInput<$PrismaModel>
    in?: string[] | ListStringFieldRefInput<$PrismaModel>
    notIn?: string[] | ListStringFieldRefInput<$PrismaModel>
    lt?: string | StringFieldRefInput<$PrismaModel>
    lte?: string | StringFieldRefInput<$PrismaModel>
    gt?: string | StringFieldRefInput<$PrismaModel>
    gte?: string | StringFieldRefInput<$PrismaModel>
    contains?: string | StringFieldRefInput<$PrismaModel>
    startsWith?: string | StringFieldRefInput<$PrismaModel>
    endsWith?: string | StringFieldRefInput<$PrismaModel>
    mode?: QueryMode
    not?: NestedStringWithAggregatesFilter<$PrismaModel> | string
    _count?: NestedIntFilter<$PrismaModel>
    _min?: NestedStringFilter<$PrismaModel>
    _max?: NestedStringFilter<$PrismaModel>
  }

  export type DateTimeWithAggregatesFilter<$PrismaModel = never> = {
    equals?: Date | string | DateTimeFieldRefInput<$PrismaModel>
    in?: Date[] | string[] | ListDateTimeFieldRefInput<$PrismaModel>
    notIn?: Date[] | string[] | ListDateTimeFieldRefInput<$PrismaModel>
    lt?: Date | string | DateTimeFieldRefInput<$PrismaModel>
    lte?: Date | string | DateTimeFieldRefInput<$PrismaModel>
    gt?: Date | string | DateTimeFieldRefInput<$PrismaModel>
    gte?: Date | string | DateTimeFieldRefInput<$PrismaModel>
    not?: NestedDateTimeWithAggregatesFilter<$PrismaModel> | Date | string
    _count?: NestedIntFilter<$PrismaModel>
    _min?: NestedDateTimeFilter<$PrismaModel>
    _max?: NestedDateTimeFilter<$PrismaModel>
  }

  export type DateTimeNullableWithAggregatesFilter<$PrismaModel = never> = {
    equals?: Date | string | DateTimeFieldRefInput<$PrismaModel> | null
    in?: Date[] | string[] | ListDateTimeFieldRefInput<$PrismaModel> | null
    notIn?: Date[] | string[] | ListDateTimeFieldRefInput<$PrismaModel> | null
    lt?: Date | string | DateTimeFieldRefInput<$PrismaModel>
    lte?: Date | string | DateTimeFieldRefInput<$PrismaModel>
    gt?: Date | string | DateTimeFieldRefInput<$PrismaModel>
    gte?: Date | string | DateTimeFieldRefInput<$PrismaModel>
    not?: NestedDateTimeNullableWithAggregatesFilter<$PrismaModel> | Date | string | null
    _count?: NestedIntNullableFilter<$PrismaModel>
    _min?: NestedDateTimeNullableFilter<$PrismaModel>
    _max?: NestedDateTimeNullableFilter<$PrismaModel>
  }

  export type BoolWithAggregatesFilter<$PrismaModel = never> = {
    equals?: boolean | BooleanFieldRefInput<$PrismaModel>
    not?: NestedBoolWithAggregatesFilter<$PrismaModel> | boolean
    _count?: NestedIntFilter<$PrismaModel>
    _min?: NestedBoolFilter<$PrismaModel>
    _max?: NestedBoolFilter<$PrismaModel>
  }

  export type ParentListRelationFilter = {
    every?: ParentWhereInput
    some?: ParentWhereInput
    none?: ParentWhereInput
  }

  export type ChildListRelationFilter = {
    every?: ChildWhereInput
    some?: ChildWhereInput
    none?: ChildWhereInput
  }

  export type ParentOrderByRelationAggregateInput = {
    _count?: SortOrder
  }

  export type ChildOrderByRelationAggregateInput = {
    _count?: SortOrder
  }

  export type FamilyCountOrderByAggregateInput = {
    id?: SortOrder
    lastParticipationDate?: SortOrder
  }

  export type FamilyMaxOrderByAggregateInput = {
    id?: SortOrder
    lastParticipationDate?: SortOrder
  }

  export type FamilyMinOrderByAggregateInput = {
    id?: SortOrder
    lastParticipationDate?: SortOrder
  }

  export type StringNullableFilter<$PrismaModel = never> = {
    equals?: string | StringFieldRefInput<$PrismaModel> | null
    in?: string[] | ListStringFieldRefInput<$PrismaModel> | null
    notIn?: string[] | ListStringFieldRefInput<$PrismaModel> | null
    lt?: string | StringFieldRefInput<$PrismaModel>
    lte?: string | StringFieldRefInput<$PrismaModel>
    gt?: string | StringFieldRefInput<$PrismaModel>
    gte?: string | StringFieldRefInput<$PrismaModel>
    contains?: string | StringFieldRefInput<$PrismaModel>
    startsWith?: string | StringFieldRefInput<$PrismaModel>
    endsWith?: string | StringFieldRefInput<$PrismaModel>
    mode?: QueryMode
    not?: NestedStringNullableFilter<$PrismaModel> | string | null
  }

  export type FamilyScalarRelationFilter = {
    is?: FamilyWhereInput
    isNot?: FamilyWhereInput
  }

  export type ParentCountOrderByAggregateInput = {
    id?: SortOrder
    name?: SortOrder
    phone?: SortOrder
    email?: SortOrder
    relationshipType?: SortOrder
    lastParticipationDate?: SortOrder
    familyId?: SortOrder
  }

  export type ParentMaxOrderByAggregateInput = {
    id?: SortOrder
    name?: SortOrder
    phone?: SortOrder
    email?: SortOrder
    relationshipType?: SortOrder
    lastParticipationDate?: SortOrder
    familyId?: SortOrder
  }

  export type ParentMinOrderByAggregateInput = {
    id?: SortOrder
    name?: SortOrder
    phone?: SortOrder
    email?: SortOrder
    relationshipType?: SortOrder
    lastParticipationDate?: SortOrder
    familyId?: SortOrder
  }

  export type StringNullableWithAggregatesFilter<$PrismaModel = never> = {
    equals?: string | StringFieldRefInput<$PrismaModel> | null
    in?: string[] | ListStringFieldRefInput<$PrismaModel> | null
    notIn?: string[] | ListStringFieldRefInput<$PrismaModel> | null
    lt?: string | StringFieldRefInput<$PrismaModel>
    lte?: string | StringFieldRefInput<$PrismaModel>
    gt?: string | StringFieldRefInput<$PrismaModel>
    gte?: string | StringFieldRefInput<$PrismaModel>
    contains?: string | StringFieldRefInput<$PrismaModel>
    startsWith?: string | StringFieldRefInput<$PrismaModel>
    endsWith?: string | StringFieldRefInput<$PrismaModel>
    mode?: QueryMode
    not?: NestedStringNullableWithAggregatesFilter<$PrismaModel> | string | null
    _count?: NestedIntNullableFilter<$PrismaModel>
    _min?: NestedStringNullableFilter<$PrismaModel>
    _max?: NestedStringNullableFilter<$PrismaModel>
  }

  export type TicketListRelationFilter = {
    every?: TicketWhereInput
    some?: TicketWhereInput
    none?: TicketWhereInput
  }

  export type TicketOrderByRelationAggregateInput = {
    _count?: SortOrder
  }

  export type ChildCountOrderByAggregateInput = {
    id?: SortOrder
    firstName?: SortOrder
    lastName?: SortOrder
    birthdate?: SortOrder
    allergies?: SortOrder
    notes?: SortOrder
    qrToken?: SortOrder
    lastParticipationDate?: SortOrder
    familyId?: SortOrder
  }

  export type ChildMaxOrderByAggregateInput = {
    id?: SortOrder
    firstName?: SortOrder
    lastName?: SortOrder
    birthdate?: SortOrder
    allergies?: SortOrder
    notes?: SortOrder
    qrToken?: SortOrder
    lastParticipationDate?: SortOrder
    familyId?: SortOrder
  }

  export type ChildMinOrderByAggregateInput = {
    id?: SortOrder
    firstName?: SortOrder
    lastName?: SortOrder
    birthdate?: SortOrder
    allergies?: SortOrder
    notes?: SortOrder
    qrToken?: SortOrder
    lastParticipationDate?: SortOrder
    familyId?: SortOrder
  }

  export type SessionListRelationFilter = {
    every?: SessionWhereInput
    some?: SessionWhereInput
    none?: SessionWhereInput
  }

  export type SessionOrderByRelationAggregateInput = {
    _count?: SortOrder
  }

  export type EventCountOrderByAggregateInput = {
    id?: SortOrder
    name?: SortOrder
    startDate?: SortOrder
    endDate?: SortOrder
  }

  export type EventMaxOrderByAggregateInput = {
    id?: SortOrder
    name?: SortOrder
    startDate?: SortOrder
    endDate?: SortOrder
  }

  export type EventMinOrderByAggregateInput = {
    id?: SortOrder
    name?: SortOrder
    startDate?: SortOrder
    endDate?: SortOrder
  }

  export type EventScalarRelationFilter = {
    is?: EventWhereInput
    isNot?: EventWhereInput
  }

  export type SessionCountOrderByAggregateInput = {
    id?: SortOrder
    name?: SortOrder
    startTime?: SortOrder
    endTime?: SortOrder
    isActive?: SortOrder
    requiresTicket?: SortOrder
    eventId?: SortOrder
  }

  export type SessionMaxOrderByAggregateInput = {
    id?: SortOrder
    name?: SortOrder
    startTime?: SortOrder
    endTime?: SortOrder
    isActive?: SortOrder
    requiresTicket?: SortOrder
    eventId?: SortOrder
  }

  export type SessionMinOrderByAggregateInput = {
    id?: SortOrder
    name?: SortOrder
    startTime?: SortOrder
    endTime?: SortOrder
    isActive?: SortOrder
    requiresTicket?: SortOrder
    eventId?: SortOrder
  }

  export type ChildScalarRelationFilter = {
    is?: ChildWhereInput
    isNot?: ChildWhereInput
  }

  export type SessionNullableScalarRelationFilter = {
    is?: SessionWhereInput | null
    isNot?: SessionWhereInput | null
  }

  export type TicketCountOrderByAggregateInput = {
    id?: SortOrder
    type?: SortOrder
    childId?: SortOrder
    sessionId?: SortOrder
  }

  export type TicketMaxOrderByAggregateInput = {
    id?: SortOrder
    type?: SortOrder
    childId?: SortOrder
    sessionId?: SortOrder
  }

  export type TicketMinOrderByAggregateInput = {
    id?: SortOrder
    type?: SortOrder
    childId?: SortOrder
    sessionId?: SortOrder
  }

  export type SessionScalarRelationFilter = {
    is?: SessionWhereInput
    isNot?: SessionWhereInput
  }

  export type AdminUserScalarRelationFilter = {
    is?: AdminUserWhereInput
    isNot?: AdminUserWhereInput
  }

  export type AdminUserNullableScalarRelationFilter = {
    is?: AdminUserWhereInput | null
    isNot?: AdminUserWhereInput | null
  }

  export type CheckInRecordChildIdSessionIdCheckInTimeCompoundUniqueInput = {
    childId: string
    sessionId: string
    checkInTime: Date | string
  }

  export type CheckInRecordCountOrderByAggregateInput = {
    id?: SortOrder
    checkInTime?: SortOrder
    checkOutTime?: SortOrder
    pickedUpBy?: SortOrder
    childId?: SortOrder
    sessionId?: SortOrder
    checkInStaffId?: SortOrder
    checkOutStaffId?: SortOrder
  }

  export type CheckInRecordMaxOrderByAggregateInput = {
    id?: SortOrder
    checkInTime?: SortOrder
    checkOutTime?: SortOrder
    pickedUpBy?: SortOrder
    childId?: SortOrder
    sessionId?: SortOrder
    checkInStaffId?: SortOrder
    checkOutStaffId?: SortOrder
  }

  export type CheckInRecordMinOrderByAggregateInput = {
    id?: SortOrder
    checkInTime?: SortOrder
    checkOutTime?: SortOrder
    pickedUpBy?: SortOrder
    childId?: SortOrder
    sessionId?: SortOrder
    checkInStaffId?: SortOrder
    checkOutStaffId?: SortOrder
  }
  export type JsonNullableFilter<$PrismaModel = never> =
    | PatchUndefined<
        Either<Required<JsonNullableFilterBase<$PrismaModel>>, Exclude<keyof Required<JsonNullableFilterBase<$PrismaModel>>, 'path'>>,
        Required<JsonNullableFilterBase<$PrismaModel>>
      >
    | OptionalFlat<Omit<Required<JsonNullableFilterBase<$PrismaModel>>, 'path'>>

  export type JsonNullableFilterBase<$PrismaModel = never> = {
    equals?: InputJsonValue | JsonFieldRefInput<$PrismaModel> | JsonNullValueFilter
    path?: string[]
    mode?: QueryMode | EnumQueryModeFieldRefInput<$PrismaModel>
    string_contains?: string | StringFieldRefInput<$PrismaModel>
    string_starts_with?: string | StringFieldRefInput<$PrismaModel>
    string_ends_with?: string | StringFieldRefInput<$PrismaModel>
    array_starts_with?: InputJsonValue | JsonFieldRefInput<$PrismaModel> | null
    array_ends_with?: InputJsonValue | JsonFieldRefInput<$PrismaModel> | null
    array_contains?: InputJsonValue | JsonFieldRefInput<$PrismaModel> | null
    lt?: InputJsonValue | JsonFieldRefInput<$PrismaModel>
    lte?: InputJsonValue | JsonFieldRefInput<$PrismaModel>
    gt?: InputJsonValue | JsonFieldRefInput<$PrismaModel>
    gte?: InputJsonValue | JsonFieldRefInput<$PrismaModel>
    not?: InputJsonValue | JsonFieldRefInput<$PrismaModel> | JsonNullValueFilter
  }

  export type AuditLogCountOrderByAggregateInput = {
    id?: SortOrder
    timestamp?: SortOrder
    userId?: SortOrder
    action?: SortOrder
    entityType?: SortOrder
    entityId?: SortOrder
    details?: SortOrder
  }

  export type AuditLogMaxOrderByAggregateInput = {
    id?: SortOrder
    timestamp?: SortOrder
    userId?: SortOrder
    action?: SortOrder
    entityType?: SortOrder
    entityId?: SortOrder
  }

  export type AuditLogMinOrderByAggregateInput = {
    id?: SortOrder
    timestamp?: SortOrder
    userId?: SortOrder
    action?: SortOrder
    entityType?: SortOrder
    entityId?: SortOrder
  }
  export type JsonNullableWithAggregatesFilter<$PrismaModel = never> =
    | PatchUndefined<
        Either<Required<JsonNullableWithAggregatesFilterBase<$PrismaModel>>, Exclude<keyof Required<JsonNullableWithAggregatesFilterBase<$PrismaModel>>, 'path'>>,
        Required<JsonNullableWithAggregatesFilterBase<$PrismaModel>>
      >
    | OptionalFlat<Omit<Required<JsonNullableWithAggregatesFilterBase<$PrismaModel>>, 'path'>>

  export type JsonNullableWithAggregatesFilterBase<$PrismaModel = never> = {
    equals?: InputJsonValue | JsonFieldRefInput<$PrismaModel> | JsonNullValueFilter
    path?: string[]
    mode?: QueryMode | EnumQueryModeFieldRefInput<$PrismaModel>
    string_contains?: string | StringFieldRefInput<$PrismaModel>
    string_starts_with?: string | StringFieldRefInput<$PrismaModel>
    string_ends_with?: string | StringFieldRefInput<$PrismaModel>
    array_starts_with?: InputJsonValue | JsonFieldRefInput<$PrismaModel> | null
    array_ends_with?: InputJsonValue | JsonFieldRefInput<$PrismaModel> | null
    array_contains?: InputJsonValue | JsonFieldRefInput<$PrismaModel> | null
    lt?: InputJsonValue | JsonFieldRefInput<$PrismaModel>
    lte?: InputJsonValue | JsonFieldRefInput<$PrismaModel>
    gt?: InputJsonValue | JsonFieldRefInput<$PrismaModel>
    gte?: InputJsonValue | JsonFieldRefInput<$PrismaModel>
    not?: InputJsonValue | JsonFieldRefInput<$PrismaModel> | JsonNullValueFilter
    _count?: NestedIntNullableFilter<$PrismaModel>
    _min?: NestedJsonNullableFilter<$PrismaModel>
    _max?: NestedJsonNullableFilter<$PrismaModel>
  }

  export type CheckInRecordCreateNestedManyWithoutCheckInStaffInput = {
    create?: XOR<CheckInRecordCreateWithoutCheckInStaffInput, CheckInRecordUncheckedCreateWithoutCheckInStaffInput> | CheckInRecordCreateWithoutCheckInStaffInput[] | CheckInRecordUncheckedCreateWithoutCheckInStaffInput[]
    connectOrCreate?: CheckInRecordCreateOrConnectWithoutCheckInStaffInput | CheckInRecordCreateOrConnectWithoutCheckInStaffInput[]
    createMany?: CheckInRecordCreateManyCheckInStaffInputEnvelope
    connect?: CheckInRecordWhereUniqueInput | CheckInRecordWhereUniqueInput[]
  }

  export type CheckInRecordCreateNestedManyWithoutCheckOutStaffInput = {
    create?: XOR<CheckInRecordCreateWithoutCheckOutStaffInput, CheckInRecordUncheckedCreateWithoutCheckOutStaffInput> | CheckInRecordCreateWithoutCheckOutStaffInput[] | CheckInRecordUncheckedCreateWithoutCheckOutStaffInput[]
    connectOrCreate?: CheckInRecordCreateOrConnectWithoutCheckOutStaffInput | CheckInRecordCreateOrConnectWithoutCheckOutStaffInput[]
    createMany?: CheckInRecordCreateManyCheckOutStaffInputEnvelope
    connect?: CheckInRecordWhereUniqueInput | CheckInRecordWhereUniqueInput[]
  }

  export type CheckInRecordUncheckedCreateNestedManyWithoutCheckInStaffInput = {
    create?: XOR<CheckInRecordCreateWithoutCheckInStaffInput, CheckInRecordUncheckedCreateWithoutCheckInStaffInput> | CheckInRecordCreateWithoutCheckInStaffInput[] | CheckInRecordUncheckedCreateWithoutCheckInStaffInput[]
    connectOrCreate?: CheckInRecordCreateOrConnectWithoutCheckInStaffInput | CheckInRecordCreateOrConnectWithoutCheckInStaffInput[]
    createMany?: CheckInRecordCreateManyCheckInStaffInputEnvelope
    connect?: CheckInRecordWhereUniqueInput | CheckInRecordWhereUniqueInput[]
  }

  export type CheckInRecordUncheckedCreateNestedManyWithoutCheckOutStaffInput = {
    create?: XOR<CheckInRecordCreateWithoutCheckOutStaffInput, CheckInRecordUncheckedCreateWithoutCheckOutStaffInput> | CheckInRecordCreateWithoutCheckOutStaffInput[] | CheckInRecordUncheckedCreateWithoutCheckOutStaffInput[]
    connectOrCreate?: CheckInRecordCreateOrConnectWithoutCheckOutStaffInput | CheckInRecordCreateOrConnectWithoutCheckOutStaffInput[]
    createMany?: CheckInRecordCreateManyCheckOutStaffInputEnvelope
    connect?: CheckInRecordWhereUniqueInput | CheckInRecordWhereUniqueInput[]
  }

  export type StringFieldUpdateOperationsInput = {
    set?: string
  }

  export type DateTimeFieldUpdateOperationsInput = {
    set?: Date | string
  }

  export type NullableDateTimeFieldUpdateOperationsInput = {
    set?: Date | string | null
  }

  export type BoolFieldUpdateOperationsInput = {
    set?: boolean
  }

  export type CheckInRecordUpdateManyWithoutCheckInStaffNestedInput = {
    create?: XOR<CheckInRecordCreateWithoutCheckInStaffInput, CheckInRecordUncheckedCreateWithoutCheckInStaffInput> | CheckInRecordCreateWithoutCheckInStaffInput[] | CheckInRecordUncheckedCreateWithoutCheckInStaffInput[]
    connectOrCreate?: CheckInRecordCreateOrConnectWithoutCheckInStaffInput | CheckInRecordCreateOrConnectWithoutCheckInStaffInput[]
    upsert?: CheckInRecordUpsertWithWhereUniqueWithoutCheckInStaffInput | CheckInRecordUpsertWithWhereUniqueWithoutCheckInStaffInput[]
    createMany?: CheckInRecordCreateManyCheckInStaffInputEnvelope
    set?: CheckInRecordWhereUniqueInput | CheckInRecordWhereUniqueInput[]
    disconnect?: CheckInRecordWhereUniqueInput | CheckInRecordWhereUniqueInput[]
    delete?: CheckInRecordWhereUniqueInput | CheckInRecordWhereUniqueInput[]
    connect?: CheckInRecordWhereUniqueInput | CheckInRecordWhereUniqueInput[]
    update?: CheckInRecordUpdateWithWhereUniqueWithoutCheckInStaffInput | CheckInRecordUpdateWithWhereUniqueWithoutCheckInStaffInput[]
    updateMany?: CheckInRecordUpdateManyWithWhereWithoutCheckInStaffInput | CheckInRecordUpdateManyWithWhereWithoutCheckInStaffInput[]
    deleteMany?: CheckInRecordScalarWhereInput | CheckInRecordScalarWhereInput[]
  }

  export type CheckInRecordUpdateManyWithoutCheckOutStaffNestedInput = {
    create?: XOR<CheckInRecordCreateWithoutCheckOutStaffInput, CheckInRecordUncheckedCreateWithoutCheckOutStaffInput> | CheckInRecordCreateWithoutCheckOutStaffInput[] | CheckInRecordUncheckedCreateWithoutCheckOutStaffInput[]
    connectOrCreate?: CheckInRecordCreateOrConnectWithoutCheckOutStaffInput | CheckInRecordCreateOrConnectWithoutCheckOutStaffInput[]
    upsert?: CheckInRecordUpsertWithWhereUniqueWithoutCheckOutStaffInput | CheckInRecordUpsertWithWhereUniqueWithoutCheckOutStaffInput[]
    createMany?: CheckInRecordCreateManyCheckOutStaffInputEnvelope
    set?: CheckInRecordWhereUniqueInput | CheckInRecordWhereUniqueInput[]
    disconnect?: CheckInRecordWhereUniqueInput | CheckInRecordWhereUniqueInput[]
    delete?: CheckInRecordWhereUniqueInput | CheckInRecordWhereUniqueInput[]
    connect?: CheckInRecordWhereUniqueInput | CheckInRecordWhereUniqueInput[]
    update?: CheckInRecordUpdateWithWhereUniqueWithoutCheckOutStaffInput | CheckInRecordUpdateWithWhereUniqueWithoutCheckOutStaffInput[]
    updateMany?: CheckInRecordUpdateManyWithWhereWithoutCheckOutStaffInput | CheckInRecordUpdateManyWithWhereWithoutCheckOutStaffInput[]
    deleteMany?: CheckInRecordScalarWhereInput | CheckInRecordScalarWhereInput[]
  }

  export type CheckInRecordUncheckedUpdateManyWithoutCheckInStaffNestedInput = {
    create?: XOR<CheckInRecordCreateWithoutCheckInStaffInput, CheckInRecordUncheckedCreateWithoutCheckInStaffInput> | CheckInRecordCreateWithoutCheckInStaffInput[] | CheckInRecordUncheckedCreateWithoutCheckInStaffInput[]
    connectOrCreate?: CheckInRecordCreateOrConnectWithoutCheckInStaffInput | CheckInRecordCreateOrConnectWithoutCheckInStaffInput[]
    upsert?: CheckInRecordUpsertWithWhereUniqueWithoutCheckInStaffInput | CheckInRecordUpsertWithWhereUniqueWithoutCheckInStaffInput[]
    createMany?: CheckInRecordCreateManyCheckInStaffInputEnvelope
    set?: CheckInRecordWhereUniqueInput | CheckInRecordWhereUniqueInput[]
    disconnect?: CheckInRecordWhereUniqueInput | CheckInRecordWhereUniqueInput[]
    delete?: CheckInRecordWhereUniqueInput | CheckInRecordWhereUniqueInput[]
    connect?: CheckInRecordWhereUniqueInput | CheckInRecordWhereUniqueInput[]
    update?: CheckInRecordUpdateWithWhereUniqueWithoutCheckInStaffInput | CheckInRecordUpdateWithWhereUniqueWithoutCheckInStaffInput[]
    updateMany?: CheckInRecordUpdateManyWithWhereWithoutCheckInStaffInput | CheckInRecordUpdateManyWithWhereWithoutCheckInStaffInput[]
    deleteMany?: CheckInRecordScalarWhereInput | CheckInRecordScalarWhereInput[]
  }

  export type CheckInRecordUncheckedUpdateManyWithoutCheckOutStaffNestedInput = {
    create?: XOR<CheckInRecordCreateWithoutCheckOutStaffInput, CheckInRecordUncheckedCreateWithoutCheckOutStaffInput> | CheckInRecordCreateWithoutCheckOutStaffInput[] | CheckInRecordUncheckedCreateWithoutCheckOutStaffInput[]
    connectOrCreate?: CheckInRecordCreateOrConnectWithoutCheckOutStaffInput | CheckInRecordCreateOrConnectWithoutCheckOutStaffInput[]
    upsert?: CheckInRecordUpsertWithWhereUniqueWithoutCheckOutStaffInput | CheckInRecordUpsertWithWhereUniqueWithoutCheckOutStaffInput[]
    createMany?: CheckInRecordCreateManyCheckOutStaffInputEnvelope
    set?: CheckInRecordWhereUniqueInput | CheckInRecordWhereUniqueInput[]
    disconnect?: CheckInRecordWhereUniqueInput | CheckInRecordWhereUniqueInput[]
    delete?: CheckInRecordWhereUniqueInput | CheckInRecordWhereUniqueInput[]
    connect?: CheckInRecordWhereUniqueInput | CheckInRecordWhereUniqueInput[]
    update?: CheckInRecordUpdateWithWhereUniqueWithoutCheckOutStaffInput | CheckInRecordUpdateWithWhereUniqueWithoutCheckOutStaffInput[]
    updateMany?: CheckInRecordUpdateManyWithWhereWithoutCheckOutStaffInput | CheckInRecordUpdateManyWithWhereWithoutCheckOutStaffInput[]
    deleteMany?: CheckInRecordScalarWhereInput | CheckInRecordScalarWhereInput[]
  }

  export type ParentCreateNestedManyWithoutFamilyInput = {
    create?: XOR<ParentCreateWithoutFamilyInput, ParentUncheckedCreateWithoutFamilyInput> | ParentCreateWithoutFamilyInput[] | ParentUncheckedCreateWithoutFamilyInput[]
    connectOrCreate?: ParentCreateOrConnectWithoutFamilyInput | ParentCreateOrConnectWithoutFamilyInput[]
    createMany?: ParentCreateManyFamilyInputEnvelope
    connect?: ParentWhereUniqueInput | ParentWhereUniqueInput[]
  }

  export type ChildCreateNestedManyWithoutFamilyInput = {
    create?: XOR<ChildCreateWithoutFamilyInput, ChildUncheckedCreateWithoutFamilyInput> | ChildCreateWithoutFamilyInput[] | ChildUncheckedCreateWithoutFamilyInput[]
    connectOrCreate?: ChildCreateOrConnectWithoutFamilyInput | ChildCreateOrConnectWithoutFamilyInput[]
    createMany?: ChildCreateManyFamilyInputEnvelope
    connect?: ChildWhereUniqueInput | ChildWhereUniqueInput[]
  }

  export type ParentUncheckedCreateNestedManyWithoutFamilyInput = {
    create?: XOR<ParentCreateWithoutFamilyInput, ParentUncheckedCreateWithoutFamilyInput> | ParentCreateWithoutFamilyInput[] | ParentUncheckedCreateWithoutFamilyInput[]
    connectOrCreate?: ParentCreateOrConnectWithoutFamilyInput | ParentCreateOrConnectWithoutFamilyInput[]
    createMany?: ParentCreateManyFamilyInputEnvelope
    connect?: ParentWhereUniqueInput | ParentWhereUniqueInput[]
  }

  export type ChildUncheckedCreateNestedManyWithoutFamilyInput = {
    create?: XOR<ChildCreateWithoutFamilyInput, ChildUncheckedCreateWithoutFamilyInput> | ChildCreateWithoutFamilyInput[] | ChildUncheckedCreateWithoutFamilyInput[]
    connectOrCreate?: ChildCreateOrConnectWithoutFamilyInput | ChildCreateOrConnectWithoutFamilyInput[]
    createMany?: ChildCreateManyFamilyInputEnvelope
    connect?: ChildWhereUniqueInput | ChildWhereUniqueInput[]
  }

  export type ParentUpdateManyWithoutFamilyNestedInput = {
    create?: XOR<ParentCreateWithoutFamilyInput, ParentUncheckedCreateWithoutFamilyInput> | ParentCreateWithoutFamilyInput[] | ParentUncheckedCreateWithoutFamilyInput[]
    connectOrCreate?: ParentCreateOrConnectWithoutFamilyInput | ParentCreateOrConnectWithoutFamilyInput[]
    upsert?: ParentUpsertWithWhereUniqueWithoutFamilyInput | ParentUpsertWithWhereUniqueWithoutFamilyInput[]
    createMany?: ParentCreateManyFamilyInputEnvelope
    set?: ParentWhereUniqueInput | ParentWhereUniqueInput[]
    disconnect?: ParentWhereUniqueInput | ParentWhereUniqueInput[]
    delete?: ParentWhereUniqueInput | ParentWhereUniqueInput[]
    connect?: ParentWhereUniqueInput | ParentWhereUniqueInput[]
    update?: ParentUpdateWithWhereUniqueWithoutFamilyInput | ParentUpdateWithWhereUniqueWithoutFamilyInput[]
    updateMany?: ParentUpdateManyWithWhereWithoutFamilyInput | ParentUpdateManyWithWhereWithoutFamilyInput[]
    deleteMany?: ParentScalarWhereInput | ParentScalarWhereInput[]
  }

  export type ChildUpdateManyWithoutFamilyNestedInput = {
    create?: XOR<ChildCreateWithoutFamilyInput, ChildUncheckedCreateWithoutFamilyInput> | ChildCreateWithoutFamilyInput[] | ChildUncheckedCreateWithoutFamilyInput[]
    connectOrCreate?: ChildCreateOrConnectWithoutFamilyInput | ChildCreateOrConnectWithoutFamilyInput[]
    upsert?: ChildUpsertWithWhereUniqueWithoutFamilyInput | ChildUpsertWithWhereUniqueWithoutFamilyInput[]
    createMany?: ChildCreateManyFamilyInputEnvelope
    set?: ChildWhereUniqueInput | ChildWhereUniqueInput[]
    disconnect?: ChildWhereUniqueInput | ChildWhereUniqueInput[]
    delete?: ChildWhereUniqueInput | ChildWhereUniqueInput[]
    connect?: ChildWhereUniqueInput | ChildWhereUniqueInput[]
    update?: ChildUpdateWithWhereUniqueWithoutFamilyInput | ChildUpdateWithWhereUniqueWithoutFamilyInput[]
    updateMany?: ChildUpdateManyWithWhereWithoutFamilyInput | ChildUpdateManyWithWhereWithoutFamilyInput[]
    deleteMany?: ChildScalarWhereInput | ChildScalarWhereInput[]
  }

  export type ParentUncheckedUpdateManyWithoutFamilyNestedInput = {
    create?: XOR<ParentCreateWithoutFamilyInput, ParentUncheckedCreateWithoutFamilyInput> | ParentCreateWithoutFamilyInput[] | ParentUncheckedCreateWithoutFamilyInput[]
    connectOrCreate?: ParentCreateOrConnectWithoutFamilyInput | ParentCreateOrConnectWithoutFamilyInput[]
    upsert?: ParentUpsertWithWhereUniqueWithoutFamilyInput | ParentUpsertWithWhereUniqueWithoutFamilyInput[]
    createMany?: ParentCreateManyFamilyInputEnvelope
    set?: ParentWhereUniqueInput | ParentWhereUniqueInput[]
    disconnect?: ParentWhereUniqueInput | ParentWhereUniqueInput[]
    delete?: ParentWhereUniqueInput | ParentWhereUniqueInput[]
    connect?: ParentWhereUniqueInput | ParentWhereUniqueInput[]
    update?: ParentUpdateWithWhereUniqueWithoutFamilyInput | ParentUpdateWithWhereUniqueWithoutFamilyInput[]
    updateMany?: ParentUpdateManyWithWhereWithoutFamilyInput | ParentUpdateManyWithWhereWithoutFamilyInput[]
    deleteMany?: ParentScalarWhereInput | ParentScalarWhereInput[]
  }

  export type ChildUncheckedUpdateManyWithoutFamilyNestedInput = {
    create?: XOR<ChildCreateWithoutFamilyInput, ChildUncheckedCreateWithoutFamilyInput> | ChildCreateWithoutFamilyInput[] | ChildUncheckedCreateWithoutFamilyInput[]
    connectOrCreate?: ChildCreateOrConnectWithoutFamilyInput | ChildCreateOrConnectWithoutFamilyInput[]
    upsert?: ChildUpsertWithWhereUniqueWithoutFamilyInput | ChildUpsertWithWhereUniqueWithoutFamilyInput[]
    createMany?: ChildCreateManyFamilyInputEnvelope
    set?: ChildWhereUniqueInput | ChildWhereUniqueInput[]
    disconnect?: ChildWhereUniqueInput | ChildWhereUniqueInput[]
    delete?: ChildWhereUniqueInput | ChildWhereUniqueInput[]
    connect?: ChildWhereUniqueInput | ChildWhereUniqueInput[]
    update?: ChildUpdateWithWhereUniqueWithoutFamilyInput | ChildUpdateWithWhereUniqueWithoutFamilyInput[]
    updateMany?: ChildUpdateManyWithWhereWithoutFamilyInput | ChildUpdateManyWithWhereWithoutFamilyInput[]
    deleteMany?: ChildScalarWhereInput | ChildScalarWhereInput[]
  }

  export type FamilyCreateNestedOneWithoutParentsInput = {
    create?: XOR<FamilyCreateWithoutParentsInput, FamilyUncheckedCreateWithoutParentsInput>
    connectOrCreate?: FamilyCreateOrConnectWithoutParentsInput
    connect?: FamilyWhereUniqueInput
  }

  export type NullableStringFieldUpdateOperationsInput = {
    set?: string | null
  }

  export type FamilyUpdateOneRequiredWithoutParentsNestedInput = {
    create?: XOR<FamilyCreateWithoutParentsInput, FamilyUncheckedCreateWithoutParentsInput>
    connectOrCreate?: FamilyCreateOrConnectWithoutParentsInput
    upsert?: FamilyUpsertWithoutParentsInput
    connect?: FamilyWhereUniqueInput
    update?: XOR<XOR<FamilyUpdateToOneWithWhereWithoutParentsInput, FamilyUpdateWithoutParentsInput>, FamilyUncheckedUpdateWithoutParentsInput>
  }

  export type FamilyCreateNestedOneWithoutChildrenInput = {
    create?: XOR<FamilyCreateWithoutChildrenInput, FamilyUncheckedCreateWithoutChildrenInput>
    connectOrCreate?: FamilyCreateOrConnectWithoutChildrenInput
    connect?: FamilyWhereUniqueInput
  }

  export type CheckInRecordCreateNestedManyWithoutChildInput = {
    create?: XOR<CheckInRecordCreateWithoutChildInput, CheckInRecordUncheckedCreateWithoutChildInput> | CheckInRecordCreateWithoutChildInput[] | CheckInRecordUncheckedCreateWithoutChildInput[]
    connectOrCreate?: CheckInRecordCreateOrConnectWithoutChildInput | CheckInRecordCreateOrConnectWithoutChildInput[]
    createMany?: CheckInRecordCreateManyChildInputEnvelope
    connect?: CheckInRecordWhereUniqueInput | CheckInRecordWhereUniqueInput[]
  }

  export type TicketCreateNestedManyWithoutChildInput = {
    create?: XOR<TicketCreateWithoutChildInput, TicketUncheckedCreateWithoutChildInput> | TicketCreateWithoutChildInput[] | TicketUncheckedCreateWithoutChildInput[]
    connectOrCreate?: TicketCreateOrConnectWithoutChildInput | TicketCreateOrConnectWithoutChildInput[]
    createMany?: TicketCreateManyChildInputEnvelope
    connect?: TicketWhereUniqueInput | TicketWhereUniqueInput[]
  }

  export type CheckInRecordUncheckedCreateNestedManyWithoutChildInput = {
    create?: XOR<CheckInRecordCreateWithoutChildInput, CheckInRecordUncheckedCreateWithoutChildInput> | CheckInRecordCreateWithoutChildInput[] | CheckInRecordUncheckedCreateWithoutChildInput[]
    connectOrCreate?: CheckInRecordCreateOrConnectWithoutChildInput | CheckInRecordCreateOrConnectWithoutChildInput[]
    createMany?: CheckInRecordCreateManyChildInputEnvelope
    connect?: CheckInRecordWhereUniqueInput | CheckInRecordWhereUniqueInput[]
  }

  export type TicketUncheckedCreateNestedManyWithoutChildInput = {
    create?: XOR<TicketCreateWithoutChildInput, TicketUncheckedCreateWithoutChildInput> | TicketCreateWithoutChildInput[] | TicketUncheckedCreateWithoutChildInput[]
    connectOrCreate?: TicketCreateOrConnectWithoutChildInput | TicketCreateOrConnectWithoutChildInput[]
    createMany?: TicketCreateManyChildInputEnvelope
    connect?: TicketWhereUniqueInput | TicketWhereUniqueInput[]
  }

  export type FamilyUpdateOneRequiredWithoutChildrenNestedInput = {
    create?: XOR<FamilyCreateWithoutChildrenInput, FamilyUncheckedCreateWithoutChildrenInput>
    connectOrCreate?: FamilyCreateOrConnectWithoutChildrenInput
    upsert?: FamilyUpsertWithoutChildrenInput
    connect?: FamilyWhereUniqueInput
    update?: XOR<XOR<FamilyUpdateToOneWithWhereWithoutChildrenInput, FamilyUpdateWithoutChildrenInput>, FamilyUncheckedUpdateWithoutChildrenInput>
  }

  export type CheckInRecordUpdateManyWithoutChildNestedInput = {
    create?: XOR<CheckInRecordCreateWithoutChildInput, CheckInRecordUncheckedCreateWithoutChildInput> | CheckInRecordCreateWithoutChildInput[] | CheckInRecordUncheckedCreateWithoutChildInput[]
    connectOrCreate?: CheckInRecordCreateOrConnectWithoutChildInput | CheckInRecordCreateOrConnectWithoutChildInput[]
    upsert?: CheckInRecordUpsertWithWhereUniqueWithoutChildInput | CheckInRecordUpsertWithWhereUniqueWithoutChildInput[]
    createMany?: CheckInRecordCreateManyChildInputEnvelope
    set?: CheckInRecordWhereUniqueInput | CheckInRecordWhereUniqueInput[]
    disconnect?: CheckInRecordWhereUniqueInput | CheckInRecordWhereUniqueInput[]
    delete?: CheckInRecordWhereUniqueInput | CheckInRecordWhereUniqueInput[]
    connect?: CheckInRecordWhereUniqueInput | CheckInRecordWhereUniqueInput[]
    update?: CheckInRecordUpdateWithWhereUniqueWithoutChildInput | CheckInRecordUpdateWithWhereUniqueWithoutChildInput[]
    updateMany?: CheckInRecordUpdateManyWithWhereWithoutChildInput | CheckInRecordUpdateManyWithWhereWithoutChildInput[]
    deleteMany?: CheckInRecordScalarWhereInput | CheckInRecordScalarWhereInput[]
  }

  export type TicketUpdateManyWithoutChildNestedInput = {
    create?: XOR<TicketCreateWithoutChildInput, TicketUncheckedCreateWithoutChildInput> | TicketCreateWithoutChildInput[] | TicketUncheckedCreateWithoutChildInput[]
    connectOrCreate?: TicketCreateOrConnectWithoutChildInput | TicketCreateOrConnectWithoutChildInput[]
    upsert?: TicketUpsertWithWhereUniqueWithoutChildInput | TicketUpsertWithWhereUniqueWithoutChildInput[]
    createMany?: TicketCreateManyChildInputEnvelope
    set?: TicketWhereUniqueInput | TicketWhereUniqueInput[]
    disconnect?: TicketWhereUniqueInput | TicketWhereUniqueInput[]
    delete?: TicketWhereUniqueInput | TicketWhereUniqueInput[]
    connect?: TicketWhereUniqueInput | TicketWhereUniqueInput[]
    update?: TicketUpdateWithWhereUniqueWithoutChildInput | TicketUpdateWithWhereUniqueWithoutChildInput[]
    updateMany?: TicketUpdateManyWithWhereWithoutChildInput | TicketUpdateManyWithWhereWithoutChildInput[]
    deleteMany?: TicketScalarWhereInput | TicketScalarWhereInput[]
  }

  export type CheckInRecordUncheckedUpdateManyWithoutChildNestedInput = {
    create?: XOR<CheckInRecordCreateWithoutChildInput, CheckInRecordUncheckedCreateWithoutChildInput> | CheckInRecordCreateWithoutChildInput[] | CheckInRecordUncheckedCreateWithoutChildInput[]
    connectOrCreate?: CheckInRecordCreateOrConnectWithoutChildInput | CheckInRecordCreateOrConnectWithoutChildInput[]
    upsert?: CheckInRecordUpsertWithWhereUniqueWithoutChildInput | CheckInRecordUpsertWithWhereUniqueWithoutChildInput[]
    createMany?: CheckInRecordCreateManyChildInputEnvelope
    set?: CheckInRecordWhereUniqueInput | CheckInRecordWhereUniqueInput[]
    disconnect?: CheckInRecordWhereUniqueInput | CheckInRecordWhereUniqueInput[]
    delete?: CheckInRecordWhereUniqueInput | CheckInRecordWhereUniqueInput[]
    connect?: CheckInRecordWhereUniqueInput | CheckInRecordWhereUniqueInput[]
    update?: CheckInRecordUpdateWithWhereUniqueWithoutChildInput | CheckInRecordUpdateWithWhereUniqueWithoutChildInput[]
    updateMany?: CheckInRecordUpdateManyWithWhereWithoutChildInput | CheckInRecordUpdateManyWithWhereWithoutChildInput[]
    deleteMany?: CheckInRecordScalarWhereInput | CheckInRecordScalarWhereInput[]
  }

  export type TicketUncheckedUpdateManyWithoutChildNestedInput = {
    create?: XOR<TicketCreateWithoutChildInput, TicketUncheckedCreateWithoutChildInput> | TicketCreateWithoutChildInput[] | TicketUncheckedCreateWithoutChildInput[]
    connectOrCreate?: TicketCreateOrConnectWithoutChildInput | TicketCreateOrConnectWithoutChildInput[]
    upsert?: TicketUpsertWithWhereUniqueWithoutChildInput | TicketUpsertWithWhereUniqueWithoutChildInput[]
    createMany?: TicketCreateManyChildInputEnvelope
    set?: TicketWhereUniqueInput | TicketWhereUniqueInput[]
    disconnect?: TicketWhereUniqueInput | TicketWhereUniqueInput[]
    delete?: TicketWhereUniqueInput | TicketWhereUniqueInput[]
    connect?: TicketWhereUniqueInput | TicketWhereUniqueInput[]
    update?: TicketUpdateWithWhereUniqueWithoutChildInput | TicketUpdateWithWhereUniqueWithoutChildInput[]
    updateMany?: TicketUpdateManyWithWhereWithoutChildInput | TicketUpdateManyWithWhereWithoutChildInput[]
    deleteMany?: TicketScalarWhereInput | TicketScalarWhereInput[]
  }

  export type SessionCreateNestedManyWithoutEventInput = {
    create?: XOR<SessionCreateWithoutEventInput, SessionUncheckedCreateWithoutEventInput> | SessionCreateWithoutEventInput[] | SessionUncheckedCreateWithoutEventInput[]
    connectOrCreate?: SessionCreateOrConnectWithoutEventInput | SessionCreateOrConnectWithoutEventInput[]
    createMany?: SessionCreateManyEventInputEnvelope
    connect?: SessionWhereUniqueInput | SessionWhereUniqueInput[]
  }

  export type SessionUncheckedCreateNestedManyWithoutEventInput = {
    create?: XOR<SessionCreateWithoutEventInput, SessionUncheckedCreateWithoutEventInput> | SessionCreateWithoutEventInput[] | SessionUncheckedCreateWithoutEventInput[]
    connectOrCreate?: SessionCreateOrConnectWithoutEventInput | SessionCreateOrConnectWithoutEventInput[]
    createMany?: SessionCreateManyEventInputEnvelope
    connect?: SessionWhereUniqueInput | SessionWhereUniqueInput[]
  }

  export type SessionUpdateManyWithoutEventNestedInput = {
    create?: XOR<SessionCreateWithoutEventInput, SessionUncheckedCreateWithoutEventInput> | SessionCreateWithoutEventInput[] | SessionUncheckedCreateWithoutEventInput[]
    connectOrCreate?: SessionCreateOrConnectWithoutEventInput | SessionCreateOrConnectWithoutEventInput[]
    upsert?: SessionUpsertWithWhereUniqueWithoutEventInput | SessionUpsertWithWhereUniqueWithoutEventInput[]
    createMany?: SessionCreateManyEventInputEnvelope
    set?: SessionWhereUniqueInput | SessionWhereUniqueInput[]
    disconnect?: SessionWhereUniqueInput | SessionWhereUniqueInput[]
    delete?: SessionWhereUniqueInput | SessionWhereUniqueInput[]
    connect?: SessionWhereUniqueInput | SessionWhereUniqueInput[]
    update?: SessionUpdateWithWhereUniqueWithoutEventInput | SessionUpdateWithWhereUniqueWithoutEventInput[]
    updateMany?: SessionUpdateManyWithWhereWithoutEventInput | SessionUpdateManyWithWhereWithoutEventInput[]
    deleteMany?: SessionScalarWhereInput | SessionScalarWhereInput[]
  }

  export type SessionUncheckedUpdateManyWithoutEventNestedInput = {
    create?: XOR<SessionCreateWithoutEventInput, SessionUncheckedCreateWithoutEventInput> | SessionCreateWithoutEventInput[] | SessionUncheckedCreateWithoutEventInput[]
    connectOrCreate?: SessionCreateOrConnectWithoutEventInput | SessionCreateOrConnectWithoutEventInput[]
    upsert?: SessionUpsertWithWhereUniqueWithoutEventInput | SessionUpsertWithWhereUniqueWithoutEventInput[]
    createMany?: SessionCreateManyEventInputEnvelope
    set?: SessionWhereUniqueInput | SessionWhereUniqueInput[]
    disconnect?: SessionWhereUniqueInput | SessionWhereUniqueInput[]
    delete?: SessionWhereUniqueInput | SessionWhereUniqueInput[]
    connect?: SessionWhereUniqueInput | SessionWhereUniqueInput[]
    update?: SessionUpdateWithWhereUniqueWithoutEventInput | SessionUpdateWithWhereUniqueWithoutEventInput[]
    updateMany?: SessionUpdateManyWithWhereWithoutEventInput | SessionUpdateManyWithWhereWithoutEventInput[]
    deleteMany?: SessionScalarWhereInput | SessionScalarWhereInput[]
  }

  export type EventCreateNestedOneWithoutSessionsInput = {
    create?: XOR<EventCreateWithoutSessionsInput, EventUncheckedCreateWithoutSessionsInput>
    connectOrCreate?: EventCreateOrConnectWithoutSessionsInput
    connect?: EventWhereUniqueInput
  }

  export type CheckInRecordCreateNestedManyWithoutSessionInput = {
    create?: XOR<CheckInRecordCreateWithoutSessionInput, CheckInRecordUncheckedCreateWithoutSessionInput> | CheckInRecordCreateWithoutSessionInput[] | CheckInRecordUncheckedCreateWithoutSessionInput[]
    connectOrCreate?: CheckInRecordCreateOrConnectWithoutSessionInput | CheckInRecordCreateOrConnectWithoutSessionInput[]
    createMany?: CheckInRecordCreateManySessionInputEnvelope
    connect?: CheckInRecordWhereUniqueInput | CheckInRecordWhereUniqueInput[]
  }

  export type TicketCreateNestedManyWithoutSessionInput = {
    create?: XOR<TicketCreateWithoutSessionInput, TicketUncheckedCreateWithoutSessionInput> | TicketCreateWithoutSessionInput[] | TicketUncheckedCreateWithoutSessionInput[]
    connectOrCreate?: TicketCreateOrConnectWithoutSessionInput | TicketCreateOrConnectWithoutSessionInput[]
    createMany?: TicketCreateManySessionInputEnvelope
    connect?: TicketWhereUniqueInput | TicketWhereUniqueInput[]
  }

  export type CheckInRecordUncheckedCreateNestedManyWithoutSessionInput = {
    create?: XOR<CheckInRecordCreateWithoutSessionInput, CheckInRecordUncheckedCreateWithoutSessionInput> | CheckInRecordCreateWithoutSessionInput[] | CheckInRecordUncheckedCreateWithoutSessionInput[]
    connectOrCreate?: CheckInRecordCreateOrConnectWithoutSessionInput | CheckInRecordCreateOrConnectWithoutSessionInput[]
    createMany?: CheckInRecordCreateManySessionInputEnvelope
    connect?: CheckInRecordWhereUniqueInput | CheckInRecordWhereUniqueInput[]
  }

  export type TicketUncheckedCreateNestedManyWithoutSessionInput = {
    create?: XOR<TicketCreateWithoutSessionInput, TicketUncheckedCreateWithoutSessionInput> | TicketCreateWithoutSessionInput[] | TicketUncheckedCreateWithoutSessionInput[]
    connectOrCreate?: TicketCreateOrConnectWithoutSessionInput | TicketCreateOrConnectWithoutSessionInput[]
    createMany?: TicketCreateManySessionInputEnvelope
    connect?: TicketWhereUniqueInput | TicketWhereUniqueInput[]
  }

  export type EventUpdateOneRequiredWithoutSessionsNestedInput = {
    create?: XOR<EventCreateWithoutSessionsInput, EventUncheckedCreateWithoutSessionsInput>
    connectOrCreate?: EventCreateOrConnectWithoutSessionsInput
    upsert?: EventUpsertWithoutSessionsInput
    connect?: EventWhereUniqueInput
    update?: XOR<XOR<EventUpdateToOneWithWhereWithoutSessionsInput, EventUpdateWithoutSessionsInput>, EventUncheckedUpdateWithoutSessionsInput>
  }

  export type CheckInRecordUpdateManyWithoutSessionNestedInput = {
    create?: XOR<CheckInRecordCreateWithoutSessionInput, CheckInRecordUncheckedCreateWithoutSessionInput> | CheckInRecordCreateWithoutSessionInput[] | CheckInRecordUncheckedCreateWithoutSessionInput[]
    connectOrCreate?: CheckInRecordCreateOrConnectWithoutSessionInput | CheckInRecordCreateOrConnectWithoutSessionInput[]
    upsert?: CheckInRecordUpsertWithWhereUniqueWithoutSessionInput | CheckInRecordUpsertWithWhereUniqueWithoutSessionInput[]
    createMany?: CheckInRecordCreateManySessionInputEnvelope
    set?: CheckInRecordWhereUniqueInput | CheckInRecordWhereUniqueInput[]
    disconnect?: CheckInRecordWhereUniqueInput | CheckInRecordWhereUniqueInput[]
    delete?: CheckInRecordWhereUniqueInput | CheckInRecordWhereUniqueInput[]
    connect?: CheckInRecordWhereUniqueInput | CheckInRecordWhereUniqueInput[]
    update?: CheckInRecordUpdateWithWhereUniqueWithoutSessionInput | CheckInRecordUpdateWithWhereUniqueWithoutSessionInput[]
    updateMany?: CheckInRecordUpdateManyWithWhereWithoutSessionInput | CheckInRecordUpdateManyWithWhereWithoutSessionInput[]
    deleteMany?: CheckInRecordScalarWhereInput | CheckInRecordScalarWhereInput[]
  }

  export type TicketUpdateManyWithoutSessionNestedInput = {
    create?: XOR<TicketCreateWithoutSessionInput, TicketUncheckedCreateWithoutSessionInput> | TicketCreateWithoutSessionInput[] | TicketUncheckedCreateWithoutSessionInput[]
    connectOrCreate?: TicketCreateOrConnectWithoutSessionInput | TicketCreateOrConnectWithoutSessionInput[]
    upsert?: TicketUpsertWithWhereUniqueWithoutSessionInput | TicketUpsertWithWhereUniqueWithoutSessionInput[]
    createMany?: TicketCreateManySessionInputEnvelope
    set?: TicketWhereUniqueInput | TicketWhereUniqueInput[]
    disconnect?: TicketWhereUniqueInput | TicketWhereUniqueInput[]
    delete?: TicketWhereUniqueInput | TicketWhereUniqueInput[]
    connect?: TicketWhereUniqueInput | TicketWhereUniqueInput[]
    update?: TicketUpdateWithWhereUniqueWithoutSessionInput | TicketUpdateWithWhereUniqueWithoutSessionInput[]
    updateMany?: TicketUpdateManyWithWhereWithoutSessionInput | TicketUpdateManyWithWhereWithoutSessionInput[]
    deleteMany?: TicketScalarWhereInput | TicketScalarWhereInput[]
  }

  export type CheckInRecordUncheckedUpdateManyWithoutSessionNestedInput = {
    create?: XOR<CheckInRecordCreateWithoutSessionInput, CheckInRecordUncheckedCreateWithoutSessionInput> | CheckInRecordCreateWithoutSessionInput[] | CheckInRecordUncheckedCreateWithoutSessionInput[]
    connectOrCreate?: CheckInRecordCreateOrConnectWithoutSessionInput | CheckInRecordCreateOrConnectWithoutSessionInput[]
    upsert?: CheckInRecordUpsertWithWhereUniqueWithoutSessionInput | CheckInRecordUpsertWithWhereUniqueWithoutSessionInput[]
    createMany?: CheckInRecordCreateManySessionInputEnvelope
    set?: CheckInRecordWhereUniqueInput | CheckInRecordWhereUniqueInput[]
    disconnect?: CheckInRecordWhereUniqueInput | CheckInRecordWhereUniqueInput[]
    delete?: CheckInRecordWhereUniqueInput | CheckInRecordWhereUniqueInput[]
    connect?: CheckInRecordWhereUniqueInput | CheckInRecordWhereUniqueInput[]
    update?: CheckInRecordUpdateWithWhereUniqueWithoutSessionInput | CheckInRecordUpdateWithWhereUniqueWithoutSessionInput[]
    updateMany?: CheckInRecordUpdateManyWithWhereWithoutSessionInput | CheckInRecordUpdateManyWithWhereWithoutSessionInput[]
    deleteMany?: CheckInRecordScalarWhereInput | CheckInRecordScalarWhereInput[]
  }

  export type TicketUncheckedUpdateManyWithoutSessionNestedInput = {
    create?: XOR<TicketCreateWithoutSessionInput, TicketUncheckedCreateWithoutSessionInput> | TicketCreateWithoutSessionInput[] | TicketUncheckedCreateWithoutSessionInput[]
    connectOrCreate?: TicketCreateOrConnectWithoutSessionInput | TicketCreateOrConnectWithoutSessionInput[]
    upsert?: TicketUpsertWithWhereUniqueWithoutSessionInput | TicketUpsertWithWhereUniqueWithoutSessionInput[]
    createMany?: TicketCreateManySessionInputEnvelope
    set?: TicketWhereUniqueInput | TicketWhereUniqueInput[]
    disconnect?: TicketWhereUniqueInput | TicketWhereUniqueInput[]
    delete?: TicketWhereUniqueInput | TicketWhereUniqueInput[]
    connect?: TicketWhereUniqueInput | TicketWhereUniqueInput[]
    update?: TicketUpdateWithWhereUniqueWithoutSessionInput | TicketUpdateWithWhereUniqueWithoutSessionInput[]
    updateMany?: TicketUpdateManyWithWhereWithoutSessionInput | TicketUpdateManyWithWhereWithoutSessionInput[]
    deleteMany?: TicketScalarWhereInput | TicketScalarWhereInput[]
  }

  export type ChildCreateNestedOneWithoutTicketsInput = {
    create?: XOR<ChildCreateWithoutTicketsInput, ChildUncheckedCreateWithoutTicketsInput>
    connectOrCreate?: ChildCreateOrConnectWithoutTicketsInput
    connect?: ChildWhereUniqueInput
  }

  export type SessionCreateNestedOneWithoutTicketsInput = {
    create?: XOR<SessionCreateWithoutTicketsInput, SessionUncheckedCreateWithoutTicketsInput>
    connectOrCreate?: SessionCreateOrConnectWithoutTicketsInput
    connect?: SessionWhereUniqueInput
  }

  export type ChildUpdateOneRequiredWithoutTicketsNestedInput = {
    create?: XOR<ChildCreateWithoutTicketsInput, ChildUncheckedCreateWithoutTicketsInput>
    connectOrCreate?: ChildCreateOrConnectWithoutTicketsInput
    upsert?: ChildUpsertWithoutTicketsInput
    connect?: ChildWhereUniqueInput
    update?: XOR<XOR<ChildUpdateToOneWithWhereWithoutTicketsInput, ChildUpdateWithoutTicketsInput>, ChildUncheckedUpdateWithoutTicketsInput>
  }

  export type SessionUpdateOneWithoutTicketsNestedInput = {
    create?: XOR<SessionCreateWithoutTicketsInput, SessionUncheckedCreateWithoutTicketsInput>
    connectOrCreate?: SessionCreateOrConnectWithoutTicketsInput
    upsert?: SessionUpsertWithoutTicketsInput
    disconnect?: SessionWhereInput | boolean
    delete?: SessionWhereInput | boolean
    connect?: SessionWhereUniqueInput
    update?: XOR<XOR<SessionUpdateToOneWithWhereWithoutTicketsInput, SessionUpdateWithoutTicketsInput>, SessionUncheckedUpdateWithoutTicketsInput>
  }

  export type ChildCreateNestedOneWithoutCheckInRecordsInput = {
    create?: XOR<ChildCreateWithoutCheckInRecordsInput, ChildUncheckedCreateWithoutCheckInRecordsInput>
    connectOrCreate?: ChildCreateOrConnectWithoutCheckInRecordsInput
    connect?: ChildWhereUniqueInput
  }

  export type SessionCreateNestedOneWithoutCheckInRecordsInput = {
    create?: XOR<SessionCreateWithoutCheckInRecordsInput, SessionUncheckedCreateWithoutCheckInRecordsInput>
    connectOrCreate?: SessionCreateOrConnectWithoutCheckInRecordsInput
    connect?: SessionWhereUniqueInput
  }

  export type AdminUserCreateNestedOneWithoutCheckInsPerformedInput = {
    create?: XOR<AdminUserCreateWithoutCheckInsPerformedInput, AdminUserUncheckedCreateWithoutCheckInsPerformedInput>
    connectOrCreate?: AdminUserCreateOrConnectWithoutCheckInsPerformedInput
    connect?: AdminUserWhereUniqueInput
  }

  export type AdminUserCreateNestedOneWithoutCheckOutsPerformedInput = {
    create?: XOR<AdminUserCreateWithoutCheckOutsPerformedInput, AdminUserUncheckedCreateWithoutCheckOutsPerformedInput>
    connectOrCreate?: AdminUserCreateOrConnectWithoutCheckOutsPerformedInput
    connect?: AdminUserWhereUniqueInput
  }

  export type ChildUpdateOneRequiredWithoutCheckInRecordsNestedInput = {
    create?: XOR<ChildCreateWithoutCheckInRecordsInput, ChildUncheckedCreateWithoutCheckInRecordsInput>
    connectOrCreate?: ChildCreateOrConnectWithoutCheckInRecordsInput
    upsert?: ChildUpsertWithoutCheckInRecordsInput
    connect?: ChildWhereUniqueInput
    update?: XOR<XOR<ChildUpdateToOneWithWhereWithoutCheckInRecordsInput, ChildUpdateWithoutCheckInRecordsInput>, ChildUncheckedUpdateWithoutCheckInRecordsInput>
  }

  export type SessionUpdateOneRequiredWithoutCheckInRecordsNestedInput = {
    create?: XOR<SessionCreateWithoutCheckInRecordsInput, SessionUncheckedCreateWithoutCheckInRecordsInput>
    connectOrCreate?: SessionCreateOrConnectWithoutCheckInRecordsInput
    upsert?: SessionUpsertWithoutCheckInRecordsInput
    connect?: SessionWhereUniqueInput
    update?: XOR<XOR<SessionUpdateToOneWithWhereWithoutCheckInRecordsInput, SessionUpdateWithoutCheckInRecordsInput>, SessionUncheckedUpdateWithoutCheckInRecordsInput>
  }

  export type AdminUserUpdateOneRequiredWithoutCheckInsPerformedNestedInput = {
    create?: XOR<AdminUserCreateWithoutCheckInsPerformedInput, AdminUserUncheckedCreateWithoutCheckInsPerformedInput>
    connectOrCreate?: AdminUserCreateOrConnectWithoutCheckInsPerformedInput
    upsert?: AdminUserUpsertWithoutCheckInsPerformedInput
    connect?: AdminUserWhereUniqueInput
    update?: XOR<XOR<AdminUserUpdateToOneWithWhereWithoutCheckInsPerformedInput, AdminUserUpdateWithoutCheckInsPerformedInput>, AdminUserUncheckedUpdateWithoutCheckInsPerformedInput>
  }

  export type AdminUserUpdateOneWithoutCheckOutsPerformedNestedInput = {
    create?: XOR<AdminUserCreateWithoutCheckOutsPerformedInput, AdminUserUncheckedCreateWithoutCheckOutsPerformedInput>
    connectOrCreate?: AdminUserCreateOrConnectWithoutCheckOutsPerformedInput
    upsert?: AdminUserUpsertWithoutCheckOutsPerformedInput
    disconnect?: AdminUserWhereInput | boolean
    delete?: AdminUserWhereInput | boolean
    connect?: AdminUserWhereUniqueInput
    update?: XOR<XOR<AdminUserUpdateToOneWithWhereWithoutCheckOutsPerformedInput, AdminUserUpdateWithoutCheckOutsPerformedInput>, AdminUserUncheckedUpdateWithoutCheckOutsPerformedInput>
  }

  export type NestedStringFilter<$PrismaModel = never> = {
    equals?: string | StringFieldRefInput<$PrismaModel>
    in?: string[] | ListStringFieldRefInput<$PrismaModel>
    notIn?: string[] | ListStringFieldRefInput<$PrismaModel>
    lt?: string | StringFieldRefInput<$PrismaModel>
    lte?: string | StringFieldRefInput<$PrismaModel>
    gt?: string | StringFieldRefInput<$PrismaModel>
    gte?: string | StringFieldRefInput<$PrismaModel>
    contains?: string | StringFieldRefInput<$PrismaModel>
    startsWith?: string | StringFieldRefInput<$PrismaModel>
    endsWith?: string | StringFieldRefInput<$PrismaModel>
    not?: NestedStringFilter<$PrismaModel> | string
  }

  export type NestedDateTimeFilter<$PrismaModel = never> = {
    equals?: Date | string | DateTimeFieldRefInput<$PrismaModel>
    in?: Date[] | string[] | ListDateTimeFieldRefInput<$PrismaModel>
    notIn?: Date[] | string[] | ListDateTimeFieldRefInput<$PrismaModel>
    lt?: Date | string | DateTimeFieldRefInput<$PrismaModel>
    lte?: Date | string | DateTimeFieldRefInput<$PrismaModel>
    gt?: Date | string | DateTimeFieldRefInput<$PrismaModel>
    gte?: Date | string | DateTimeFieldRefInput<$PrismaModel>
    not?: NestedDateTimeFilter<$PrismaModel> | Date | string
  }

  export type NestedDateTimeNullableFilter<$PrismaModel = never> = {
    equals?: Date | string | DateTimeFieldRefInput<$PrismaModel> | null
    in?: Date[] | string[] | ListDateTimeFieldRefInput<$PrismaModel> | null
    notIn?: Date[] | string[] | ListDateTimeFieldRefInput<$PrismaModel> | null
    lt?: Date | string | DateTimeFieldRefInput<$PrismaModel>
    lte?: Date | string | DateTimeFieldRefInput<$PrismaModel>
    gt?: Date | string | DateTimeFieldRefInput<$PrismaModel>
    gte?: Date | string | DateTimeFieldRefInput<$PrismaModel>
    not?: NestedDateTimeNullableFilter<$PrismaModel> | Date | string | null
  }

  export type NestedBoolFilter<$PrismaModel = never> = {
    equals?: boolean | BooleanFieldRefInput<$PrismaModel>
    not?: NestedBoolFilter<$PrismaModel> | boolean
  }

  export type NestedStringWithAggregatesFilter<$PrismaModel = never> = {
    equals?: string | StringFieldRefInput<$PrismaModel>
    in?: string[] | ListStringFieldRefInput<$PrismaModel>
    notIn?: string[] | ListStringFieldRefInput<$PrismaModel>
    lt?: string | StringFieldRefInput<$PrismaModel>
    lte?: string | StringFieldRefInput<$PrismaModel>
    gt?: string | StringFieldRefInput<$PrismaModel>
    gte?: string | StringFieldRefInput<$PrismaModel>
    contains?: string | StringFieldRefInput<$PrismaModel>
    startsWith?: string | StringFieldRefInput<$PrismaModel>
    endsWith?: string | StringFieldRefInput<$PrismaModel>
    not?: NestedStringWithAggregatesFilter<$PrismaModel> | string
    _count?: NestedIntFilter<$PrismaModel>
    _min?: NestedStringFilter<$PrismaModel>
    _max?: NestedStringFilter<$PrismaModel>
  }

  export type NestedIntFilter<$PrismaModel = never> = {
    equals?: number | IntFieldRefInput<$PrismaModel>
    in?: number[] | ListIntFieldRefInput<$PrismaModel>
    notIn?: number[] | ListIntFieldRefInput<$PrismaModel>
    lt?: number | IntFieldRefInput<$PrismaModel>
    lte?: number | IntFieldRefInput<$PrismaModel>
    gt?: number | IntFieldRefInput<$PrismaModel>
    gte?: number | IntFieldRefInput<$PrismaModel>
    not?: NestedIntFilter<$PrismaModel> | number
  }

  export type NestedDateTimeWithAggregatesFilter<$PrismaModel = never> = {
    equals?: Date | string | DateTimeFieldRefInput<$PrismaModel>
    in?: Date[] | string[] | ListDateTimeFieldRefInput<$PrismaModel>
    notIn?: Date[] | string[] | ListDateTimeFieldRefInput<$PrismaModel>
    lt?: Date | string | DateTimeFieldRefInput<$PrismaModel>
    lte?: Date | string | DateTimeFieldRefInput<$PrismaModel>
    gt?: Date | string | DateTimeFieldRefInput<$PrismaModel>
    gte?: Date | string | DateTimeFieldRefInput<$PrismaModel>
    not?: NestedDateTimeWithAggregatesFilter<$PrismaModel> | Date | string
    _count?: NestedIntFilter<$PrismaModel>
    _min?: NestedDateTimeFilter<$PrismaModel>
    _max?: NestedDateTimeFilter<$PrismaModel>
  }

  export type NestedDateTimeNullableWithAggregatesFilter<$PrismaModel = never> = {
    equals?: Date | string | DateTimeFieldRefInput<$PrismaModel> | null
    in?: Date[] | string[] | ListDateTimeFieldRefInput<$PrismaModel> | null
    notIn?: Date[] | string[] | ListDateTimeFieldRefInput<$PrismaModel> | null
    lt?: Date | string | DateTimeFieldRefInput<$PrismaModel>
    lte?: Date | string | DateTimeFieldRefInput<$PrismaModel>
    gt?: Date | string | DateTimeFieldRefInput<$PrismaModel>
    gte?: Date | string | DateTimeFieldRefInput<$PrismaModel>
    not?: NestedDateTimeNullableWithAggregatesFilter<$PrismaModel> | Date | string | null
    _count?: NestedIntNullableFilter<$PrismaModel>
    _min?: NestedDateTimeNullableFilter<$PrismaModel>
    _max?: NestedDateTimeNullableFilter<$PrismaModel>
  }

  export type NestedIntNullableFilter<$PrismaModel = never> = {
    equals?: number | IntFieldRefInput<$PrismaModel> | null
    in?: number[] | ListIntFieldRefInput<$PrismaModel> | null
    notIn?: number[] | ListIntFieldRefInput<$PrismaModel> | null
    lt?: number | IntFieldRefInput<$PrismaModel>
    lte?: number | IntFieldRefInput<$PrismaModel>
    gt?: number | IntFieldRefInput<$PrismaModel>
    gte?: number | IntFieldRefInput<$PrismaModel>
    not?: NestedIntNullableFilter<$PrismaModel> | number | null
  }

  export type NestedBoolWithAggregatesFilter<$PrismaModel = never> = {
    equals?: boolean | BooleanFieldRefInput<$PrismaModel>
    not?: NestedBoolWithAggregatesFilter<$PrismaModel> | boolean
    _count?: NestedIntFilter<$PrismaModel>
    _min?: NestedBoolFilter<$PrismaModel>
    _max?: NestedBoolFilter<$PrismaModel>
  }

  export type NestedStringNullableFilter<$PrismaModel = never> = {
    equals?: string | StringFieldRefInput<$PrismaModel> | null
    in?: string[] | ListStringFieldRefInput<$PrismaModel> | null
    notIn?: string[] | ListStringFieldRefInput<$PrismaModel> | null
    lt?: string | StringFieldRefInput<$PrismaModel>
    lte?: string | StringFieldRefInput<$PrismaModel>
    gt?: string | StringFieldRefInput<$PrismaModel>
    gte?: string | StringFieldRefInput<$PrismaModel>
    contains?: string | StringFieldRefInput<$PrismaModel>
    startsWith?: string | StringFieldRefInput<$PrismaModel>
    endsWith?: string | StringFieldRefInput<$PrismaModel>
    not?: NestedStringNullableFilter<$PrismaModel> | string | null
  }

  export type NestedStringNullableWithAggregatesFilter<$PrismaModel = never> = {
    equals?: string | StringFieldRefInput<$PrismaModel> | null
    in?: string[] | ListStringFieldRefInput<$PrismaModel> | null
    notIn?: string[] | ListStringFieldRefInput<$PrismaModel> | null
    lt?: string | StringFieldRefInput<$PrismaModel>
    lte?: string | StringFieldRefInput<$PrismaModel>
    gt?: string | StringFieldRefInput<$PrismaModel>
    gte?: string | StringFieldRefInput<$PrismaModel>
    contains?: string | StringFieldRefInput<$PrismaModel>
    startsWith?: string | StringFieldRefInput<$PrismaModel>
    endsWith?: string | StringFieldRefInput<$PrismaModel>
    not?: NestedStringNullableWithAggregatesFilter<$PrismaModel> | string | null
    _count?: NestedIntNullableFilter<$PrismaModel>
    _min?: NestedStringNullableFilter<$PrismaModel>
    _max?: NestedStringNullableFilter<$PrismaModel>
  }
  export type NestedJsonNullableFilter<$PrismaModel = never> =
    | PatchUndefined<
        Either<Required<NestedJsonNullableFilterBase<$PrismaModel>>, Exclude<keyof Required<NestedJsonNullableFilterBase<$PrismaModel>>, 'path'>>,
        Required<NestedJsonNullableFilterBase<$PrismaModel>>
      >
    | OptionalFlat<Omit<Required<NestedJsonNullableFilterBase<$PrismaModel>>, 'path'>>

  export type NestedJsonNullableFilterBase<$PrismaModel = never> = {
    equals?: InputJsonValue | JsonFieldRefInput<$PrismaModel> | JsonNullValueFilter
    path?: string[]
    mode?: QueryMode | EnumQueryModeFieldRefInput<$PrismaModel>
    string_contains?: string | StringFieldRefInput<$PrismaModel>
    string_starts_with?: string | StringFieldRefInput<$PrismaModel>
    string_ends_with?: string | StringFieldRefInput<$PrismaModel>
    array_starts_with?: InputJsonValue | JsonFieldRefInput<$PrismaModel> | null
    array_ends_with?: InputJsonValue | JsonFieldRefInput<$PrismaModel> | null
    array_contains?: InputJsonValue | JsonFieldRefInput<$PrismaModel> | null
    lt?: InputJsonValue | JsonFieldRefInput<$PrismaModel>
    lte?: InputJsonValue | JsonFieldRefInput<$PrismaModel>
    gt?: InputJsonValue | JsonFieldRefInput<$PrismaModel>
    gte?: InputJsonValue | JsonFieldRefInput<$PrismaModel>
    not?: InputJsonValue | JsonFieldRefInput<$PrismaModel> | JsonNullValueFilter
  }

  export type CheckInRecordCreateWithoutCheckInStaffInput = {
    id?: string
    checkInTime?: Date | string
    checkOutTime?: Date | string | null
    pickedUpBy?: string | null
    child: ChildCreateNestedOneWithoutCheckInRecordsInput
    session: SessionCreateNestedOneWithoutCheckInRecordsInput
    checkOutStaff?: AdminUserCreateNestedOneWithoutCheckOutsPerformedInput
  }

  export type CheckInRecordUncheckedCreateWithoutCheckInStaffInput = {
    id?: string
    checkInTime?: Date | string
    checkOutTime?: Date | string | null
    pickedUpBy?: string | null
    childId: string
    sessionId: string
    checkOutStaffId?: string | null
  }

  export type CheckInRecordCreateOrConnectWithoutCheckInStaffInput = {
    where: CheckInRecordWhereUniqueInput
    create: XOR<CheckInRecordCreateWithoutCheckInStaffInput, CheckInRecordUncheckedCreateWithoutCheckInStaffInput>
  }

  export type CheckInRecordCreateManyCheckInStaffInputEnvelope = {
    data: CheckInRecordCreateManyCheckInStaffInput | CheckInRecordCreateManyCheckInStaffInput[]
    skipDuplicates?: boolean
  }

  export type CheckInRecordCreateWithoutCheckOutStaffInput = {
    id?: string
    checkInTime?: Date | string
    checkOutTime?: Date | string | null
    pickedUpBy?: string | null
    child: ChildCreateNestedOneWithoutCheckInRecordsInput
    session: SessionCreateNestedOneWithoutCheckInRecordsInput
    checkInStaff: AdminUserCreateNestedOneWithoutCheckInsPerformedInput
  }

  export type CheckInRecordUncheckedCreateWithoutCheckOutStaffInput = {
    id?: string
    checkInTime?: Date | string
    checkOutTime?: Date | string | null
    pickedUpBy?: string | null
    childId: string
    sessionId: string
    checkInStaffId: string
  }

  export type CheckInRecordCreateOrConnectWithoutCheckOutStaffInput = {
    where: CheckInRecordWhereUniqueInput
    create: XOR<CheckInRecordCreateWithoutCheckOutStaffInput, CheckInRecordUncheckedCreateWithoutCheckOutStaffInput>
  }

  export type CheckInRecordCreateManyCheckOutStaffInputEnvelope = {
    data: CheckInRecordCreateManyCheckOutStaffInput | CheckInRecordCreateManyCheckOutStaffInput[]
    skipDuplicates?: boolean
  }

  export type CheckInRecordUpsertWithWhereUniqueWithoutCheckInStaffInput = {
    where: CheckInRecordWhereUniqueInput
    update: XOR<CheckInRecordUpdateWithoutCheckInStaffInput, CheckInRecordUncheckedUpdateWithoutCheckInStaffInput>
    create: XOR<CheckInRecordCreateWithoutCheckInStaffInput, CheckInRecordUncheckedCreateWithoutCheckInStaffInput>
  }

  export type CheckInRecordUpdateWithWhereUniqueWithoutCheckInStaffInput = {
    where: CheckInRecordWhereUniqueInput
    data: XOR<CheckInRecordUpdateWithoutCheckInStaffInput, CheckInRecordUncheckedUpdateWithoutCheckInStaffInput>
  }

  export type CheckInRecordUpdateManyWithWhereWithoutCheckInStaffInput = {
    where: CheckInRecordScalarWhereInput
    data: XOR<CheckInRecordUpdateManyMutationInput, CheckInRecordUncheckedUpdateManyWithoutCheckInStaffInput>
  }

  export type CheckInRecordScalarWhereInput = {
    AND?: CheckInRecordScalarWhereInput | CheckInRecordScalarWhereInput[]
    OR?: CheckInRecordScalarWhereInput[]
    NOT?: CheckInRecordScalarWhereInput | CheckInRecordScalarWhereInput[]
    id?: StringFilter<"CheckInRecord"> | string
    checkInTime?: DateTimeFilter<"CheckInRecord"> | Date | string
    checkOutTime?: DateTimeNullableFilter<"CheckInRecord"> | Date | string | null
    pickedUpBy?: StringNullableFilter<"CheckInRecord"> | string | null
    childId?: StringFilter<"CheckInRecord"> | string
    sessionId?: StringFilter<"CheckInRecord"> | string
    checkInStaffId?: StringFilter<"CheckInRecord"> | string
    checkOutStaffId?: StringNullableFilter<"CheckInRecord"> | string | null
  }

  export type CheckInRecordUpsertWithWhereUniqueWithoutCheckOutStaffInput = {
    where: CheckInRecordWhereUniqueInput
    update: XOR<CheckInRecordUpdateWithoutCheckOutStaffInput, CheckInRecordUncheckedUpdateWithoutCheckOutStaffInput>
    create: XOR<CheckInRecordCreateWithoutCheckOutStaffInput, CheckInRecordUncheckedCreateWithoutCheckOutStaffInput>
  }

  export type CheckInRecordUpdateWithWhereUniqueWithoutCheckOutStaffInput = {
    where: CheckInRecordWhereUniqueInput
    data: XOR<CheckInRecordUpdateWithoutCheckOutStaffInput, CheckInRecordUncheckedUpdateWithoutCheckOutStaffInput>
  }

  export type CheckInRecordUpdateManyWithWhereWithoutCheckOutStaffInput = {
    where: CheckInRecordScalarWhereInput
    data: XOR<CheckInRecordUpdateManyMutationInput, CheckInRecordUncheckedUpdateManyWithoutCheckOutStaffInput>
  }

  export type ParentCreateWithoutFamilyInput = {
    id?: string
    name: string
    phone?: string | null
    email?: string | null
    relationshipType: string
    lastParticipationDate?: Date | string | null
  }

  export type ParentUncheckedCreateWithoutFamilyInput = {
    id?: string
    name: string
    phone?: string | null
    email?: string | null
    relationshipType: string
    lastParticipationDate?: Date | string | null
  }

  export type ParentCreateOrConnectWithoutFamilyInput = {
    where: ParentWhereUniqueInput
    create: XOR<ParentCreateWithoutFamilyInput, ParentUncheckedCreateWithoutFamilyInput>
  }

  export type ParentCreateManyFamilyInputEnvelope = {
    data: ParentCreateManyFamilyInput | ParentCreateManyFamilyInput[]
    skipDuplicates?: boolean
  }

  export type ChildCreateWithoutFamilyInput = {
    id?: string
    firstName: string
    lastName: string
    birthdate: Date | string
    allergies?: string | null
    notes?: string | null
    qrToken?: string | null
    lastParticipationDate?: Date | string | null
    checkInRecords?: CheckInRecordCreateNestedManyWithoutChildInput
    tickets?: TicketCreateNestedManyWithoutChildInput
  }

  export type ChildUncheckedCreateWithoutFamilyInput = {
    id?: string
    firstName: string
    lastName: string
    birthdate: Date | string
    allergies?: string | null
    notes?: string | null
    qrToken?: string | null
    lastParticipationDate?: Date | string | null
    checkInRecords?: CheckInRecordUncheckedCreateNestedManyWithoutChildInput
    tickets?: TicketUncheckedCreateNestedManyWithoutChildInput
  }

  export type ChildCreateOrConnectWithoutFamilyInput = {
    where: ChildWhereUniqueInput
    create: XOR<ChildCreateWithoutFamilyInput, ChildUncheckedCreateWithoutFamilyInput>
  }

  export type ChildCreateManyFamilyInputEnvelope = {
    data: ChildCreateManyFamilyInput | ChildCreateManyFamilyInput[]
    skipDuplicates?: boolean
  }

  export type ParentUpsertWithWhereUniqueWithoutFamilyInput = {
    where: ParentWhereUniqueInput
    update: XOR<ParentUpdateWithoutFamilyInput, ParentUncheckedUpdateWithoutFamilyInput>
    create: XOR<ParentCreateWithoutFamilyInput, ParentUncheckedCreateWithoutFamilyInput>
  }

  export type ParentUpdateWithWhereUniqueWithoutFamilyInput = {
    where: ParentWhereUniqueInput
    data: XOR<ParentUpdateWithoutFamilyInput, ParentUncheckedUpdateWithoutFamilyInput>
  }

  export type ParentUpdateManyWithWhereWithoutFamilyInput = {
    where: ParentScalarWhereInput
    data: XOR<ParentUpdateManyMutationInput, ParentUncheckedUpdateManyWithoutFamilyInput>
  }

  export type ParentScalarWhereInput = {
    AND?: ParentScalarWhereInput | ParentScalarWhereInput[]
    OR?: ParentScalarWhereInput[]
    NOT?: ParentScalarWhereInput | ParentScalarWhereInput[]
    id?: StringFilter<"Parent"> | string
    name?: StringFilter<"Parent"> | string
    phone?: StringNullableFilter<"Parent"> | string | null
    email?: StringNullableFilter<"Parent"> | string | null
    relationshipType?: StringFilter<"Parent"> | string
    lastParticipationDate?: DateTimeNullableFilter<"Parent"> | Date | string | null
    familyId?: StringFilter<"Parent"> | string
  }

  export type ChildUpsertWithWhereUniqueWithoutFamilyInput = {
    where: ChildWhereUniqueInput
    update: XOR<ChildUpdateWithoutFamilyInput, ChildUncheckedUpdateWithoutFamilyInput>
    create: XOR<ChildCreateWithoutFamilyInput, ChildUncheckedCreateWithoutFamilyInput>
  }

  export type ChildUpdateWithWhereUniqueWithoutFamilyInput = {
    where: ChildWhereUniqueInput
    data: XOR<ChildUpdateWithoutFamilyInput, ChildUncheckedUpdateWithoutFamilyInput>
  }

  export type ChildUpdateManyWithWhereWithoutFamilyInput = {
    where: ChildScalarWhereInput
    data: XOR<ChildUpdateManyMutationInput, ChildUncheckedUpdateManyWithoutFamilyInput>
  }

  export type ChildScalarWhereInput = {
    AND?: ChildScalarWhereInput | ChildScalarWhereInput[]
    OR?: ChildScalarWhereInput[]
    NOT?: ChildScalarWhereInput | ChildScalarWhereInput[]
    id?: StringFilter<"Child"> | string
    firstName?: StringFilter<"Child"> | string
    lastName?: StringFilter<"Child"> | string
    birthdate?: DateTimeFilter<"Child"> | Date | string
    allergies?: StringNullableFilter<"Child"> | string | null
    notes?: StringNullableFilter<"Child"> | string | null
    qrToken?: StringNullableFilter<"Child"> | string | null
    lastParticipationDate?: DateTimeNullableFilter<"Child"> | Date | string | null
    familyId?: StringFilter<"Child"> | string
  }

  export type FamilyCreateWithoutParentsInput = {
    id?: string
    lastParticipationDate?: Date | string | null
    children?: ChildCreateNestedManyWithoutFamilyInput
  }

  export type FamilyUncheckedCreateWithoutParentsInput = {
    id?: string
    lastParticipationDate?: Date | string | null
    children?: ChildUncheckedCreateNestedManyWithoutFamilyInput
  }

  export type FamilyCreateOrConnectWithoutParentsInput = {
    where: FamilyWhereUniqueInput
    create: XOR<FamilyCreateWithoutParentsInput, FamilyUncheckedCreateWithoutParentsInput>
  }

  export type FamilyUpsertWithoutParentsInput = {
    update: XOR<FamilyUpdateWithoutParentsInput, FamilyUncheckedUpdateWithoutParentsInput>
    create: XOR<FamilyCreateWithoutParentsInput, FamilyUncheckedCreateWithoutParentsInput>
    where?: FamilyWhereInput
  }

  export type FamilyUpdateToOneWithWhereWithoutParentsInput = {
    where?: FamilyWhereInput
    data: XOR<FamilyUpdateWithoutParentsInput, FamilyUncheckedUpdateWithoutParentsInput>
  }

  export type FamilyUpdateWithoutParentsInput = {
    id?: StringFieldUpdateOperationsInput | string
    lastParticipationDate?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    children?: ChildUpdateManyWithoutFamilyNestedInput
  }

  export type FamilyUncheckedUpdateWithoutParentsInput = {
    id?: StringFieldUpdateOperationsInput | string
    lastParticipationDate?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    children?: ChildUncheckedUpdateManyWithoutFamilyNestedInput
  }

  export type FamilyCreateWithoutChildrenInput = {
    id?: string
    lastParticipationDate?: Date | string | null
    parents?: ParentCreateNestedManyWithoutFamilyInput
  }

  export type FamilyUncheckedCreateWithoutChildrenInput = {
    id?: string
    lastParticipationDate?: Date | string | null
    parents?: ParentUncheckedCreateNestedManyWithoutFamilyInput
  }

  export type FamilyCreateOrConnectWithoutChildrenInput = {
    where: FamilyWhereUniqueInput
    create: XOR<FamilyCreateWithoutChildrenInput, FamilyUncheckedCreateWithoutChildrenInput>
  }

  export type CheckInRecordCreateWithoutChildInput = {
    id?: string
    checkInTime?: Date | string
    checkOutTime?: Date | string | null
    pickedUpBy?: string | null
    session: SessionCreateNestedOneWithoutCheckInRecordsInput
    checkInStaff: AdminUserCreateNestedOneWithoutCheckInsPerformedInput
    checkOutStaff?: AdminUserCreateNestedOneWithoutCheckOutsPerformedInput
  }

  export type CheckInRecordUncheckedCreateWithoutChildInput = {
    id?: string
    checkInTime?: Date | string
    checkOutTime?: Date | string | null
    pickedUpBy?: string | null
    sessionId: string
    checkInStaffId: string
    checkOutStaffId?: string | null
  }

  export type CheckInRecordCreateOrConnectWithoutChildInput = {
    where: CheckInRecordWhereUniqueInput
    create: XOR<CheckInRecordCreateWithoutChildInput, CheckInRecordUncheckedCreateWithoutChildInput>
  }

  export type CheckInRecordCreateManyChildInputEnvelope = {
    data: CheckInRecordCreateManyChildInput | CheckInRecordCreateManyChildInput[]
    skipDuplicates?: boolean
  }

  export type TicketCreateWithoutChildInput = {
    id?: string
    type: string
    session?: SessionCreateNestedOneWithoutTicketsInput
  }

  export type TicketUncheckedCreateWithoutChildInput = {
    id?: string
    type: string
    sessionId?: string | null
  }

  export type TicketCreateOrConnectWithoutChildInput = {
    where: TicketWhereUniqueInput
    create: XOR<TicketCreateWithoutChildInput, TicketUncheckedCreateWithoutChildInput>
  }

  export type TicketCreateManyChildInputEnvelope = {
    data: TicketCreateManyChildInput | TicketCreateManyChildInput[]
    skipDuplicates?: boolean
  }

  export type FamilyUpsertWithoutChildrenInput = {
    update: XOR<FamilyUpdateWithoutChildrenInput, FamilyUncheckedUpdateWithoutChildrenInput>
    create: XOR<FamilyCreateWithoutChildrenInput, FamilyUncheckedCreateWithoutChildrenInput>
    where?: FamilyWhereInput
  }

  export type FamilyUpdateToOneWithWhereWithoutChildrenInput = {
    where?: FamilyWhereInput
    data: XOR<FamilyUpdateWithoutChildrenInput, FamilyUncheckedUpdateWithoutChildrenInput>
  }

  export type FamilyUpdateWithoutChildrenInput = {
    id?: StringFieldUpdateOperationsInput | string
    lastParticipationDate?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    parents?: ParentUpdateManyWithoutFamilyNestedInput
  }

  export type FamilyUncheckedUpdateWithoutChildrenInput = {
    id?: StringFieldUpdateOperationsInput | string
    lastParticipationDate?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    parents?: ParentUncheckedUpdateManyWithoutFamilyNestedInput
  }

  export type CheckInRecordUpsertWithWhereUniqueWithoutChildInput = {
    where: CheckInRecordWhereUniqueInput
    update: XOR<CheckInRecordUpdateWithoutChildInput, CheckInRecordUncheckedUpdateWithoutChildInput>
    create: XOR<CheckInRecordCreateWithoutChildInput, CheckInRecordUncheckedCreateWithoutChildInput>
  }

  export type CheckInRecordUpdateWithWhereUniqueWithoutChildInput = {
    where: CheckInRecordWhereUniqueInput
    data: XOR<CheckInRecordUpdateWithoutChildInput, CheckInRecordUncheckedUpdateWithoutChildInput>
  }

  export type CheckInRecordUpdateManyWithWhereWithoutChildInput = {
    where: CheckInRecordScalarWhereInput
    data: XOR<CheckInRecordUpdateManyMutationInput, CheckInRecordUncheckedUpdateManyWithoutChildInput>
  }

  export type TicketUpsertWithWhereUniqueWithoutChildInput = {
    where: TicketWhereUniqueInput
    update: XOR<TicketUpdateWithoutChildInput, TicketUncheckedUpdateWithoutChildInput>
    create: XOR<TicketCreateWithoutChildInput, TicketUncheckedCreateWithoutChildInput>
  }

  export type TicketUpdateWithWhereUniqueWithoutChildInput = {
    where: TicketWhereUniqueInput
    data: XOR<TicketUpdateWithoutChildInput, TicketUncheckedUpdateWithoutChildInput>
  }

  export type TicketUpdateManyWithWhereWithoutChildInput = {
    where: TicketScalarWhereInput
    data: XOR<TicketUpdateManyMutationInput, TicketUncheckedUpdateManyWithoutChildInput>
  }

  export type TicketScalarWhereInput = {
    AND?: TicketScalarWhereInput | TicketScalarWhereInput[]
    OR?: TicketScalarWhereInput[]
    NOT?: TicketScalarWhereInput | TicketScalarWhereInput[]
    id?: StringFilter<"Ticket"> | string
    type?: StringFilter<"Ticket"> | string
    childId?: StringFilter<"Ticket"> | string
    sessionId?: StringNullableFilter<"Ticket"> | string | null
  }

  export type SessionCreateWithoutEventInput = {
    id?: string
    name: string
    startTime: Date | string
    endTime: Date | string
    isActive?: boolean
    requiresTicket?: boolean
    checkInRecords?: CheckInRecordCreateNestedManyWithoutSessionInput
    tickets?: TicketCreateNestedManyWithoutSessionInput
  }

  export type SessionUncheckedCreateWithoutEventInput = {
    id?: string
    name: string
    startTime: Date | string
    endTime: Date | string
    isActive?: boolean
    requiresTicket?: boolean
    checkInRecords?: CheckInRecordUncheckedCreateNestedManyWithoutSessionInput
    tickets?: TicketUncheckedCreateNestedManyWithoutSessionInput
  }

  export type SessionCreateOrConnectWithoutEventInput = {
    where: SessionWhereUniqueInput
    create: XOR<SessionCreateWithoutEventInput, SessionUncheckedCreateWithoutEventInput>
  }

  export type SessionCreateManyEventInputEnvelope = {
    data: SessionCreateManyEventInput | SessionCreateManyEventInput[]
    skipDuplicates?: boolean
  }

  export type SessionUpsertWithWhereUniqueWithoutEventInput = {
    where: SessionWhereUniqueInput
    update: XOR<SessionUpdateWithoutEventInput, SessionUncheckedUpdateWithoutEventInput>
    create: XOR<SessionCreateWithoutEventInput, SessionUncheckedCreateWithoutEventInput>
  }

  export type SessionUpdateWithWhereUniqueWithoutEventInput = {
    where: SessionWhereUniqueInput
    data: XOR<SessionUpdateWithoutEventInput, SessionUncheckedUpdateWithoutEventInput>
  }

  export type SessionUpdateManyWithWhereWithoutEventInput = {
    where: SessionScalarWhereInput
    data: XOR<SessionUpdateManyMutationInput, SessionUncheckedUpdateManyWithoutEventInput>
  }

  export type SessionScalarWhereInput = {
    AND?: SessionScalarWhereInput | SessionScalarWhereInput[]
    OR?: SessionScalarWhereInput[]
    NOT?: SessionScalarWhereInput | SessionScalarWhereInput[]
    id?: StringFilter<"Session"> | string
    name?: StringFilter<"Session"> | string
    startTime?: DateTimeFilter<"Session"> | Date | string
    endTime?: DateTimeFilter<"Session"> | Date | string
    isActive?: BoolFilter<"Session"> | boolean
    requiresTicket?: BoolFilter<"Session"> | boolean
    eventId?: StringFilter<"Session"> | string
  }

  export type EventCreateWithoutSessionsInput = {
    id?: string
    name: string
    startDate: Date | string
    endDate: Date | string
  }

  export type EventUncheckedCreateWithoutSessionsInput = {
    id?: string
    name: string
    startDate: Date | string
    endDate: Date | string
  }

  export type EventCreateOrConnectWithoutSessionsInput = {
    where: EventWhereUniqueInput
    create: XOR<EventCreateWithoutSessionsInput, EventUncheckedCreateWithoutSessionsInput>
  }

  export type CheckInRecordCreateWithoutSessionInput = {
    id?: string
    checkInTime?: Date | string
    checkOutTime?: Date | string | null
    pickedUpBy?: string | null
    child: ChildCreateNestedOneWithoutCheckInRecordsInput
    checkInStaff: AdminUserCreateNestedOneWithoutCheckInsPerformedInput
    checkOutStaff?: AdminUserCreateNestedOneWithoutCheckOutsPerformedInput
  }

  export type CheckInRecordUncheckedCreateWithoutSessionInput = {
    id?: string
    checkInTime?: Date | string
    checkOutTime?: Date | string | null
    pickedUpBy?: string | null
    childId: string
    checkInStaffId: string
    checkOutStaffId?: string | null
  }

  export type CheckInRecordCreateOrConnectWithoutSessionInput = {
    where: CheckInRecordWhereUniqueInput
    create: XOR<CheckInRecordCreateWithoutSessionInput, CheckInRecordUncheckedCreateWithoutSessionInput>
  }

  export type CheckInRecordCreateManySessionInputEnvelope = {
    data: CheckInRecordCreateManySessionInput | CheckInRecordCreateManySessionInput[]
    skipDuplicates?: boolean
  }

  export type TicketCreateWithoutSessionInput = {
    id?: string
    type: string
    child: ChildCreateNestedOneWithoutTicketsInput
  }

  export type TicketUncheckedCreateWithoutSessionInput = {
    id?: string
    type: string
    childId: string
  }

  export type TicketCreateOrConnectWithoutSessionInput = {
    where: TicketWhereUniqueInput
    create: XOR<TicketCreateWithoutSessionInput, TicketUncheckedCreateWithoutSessionInput>
  }

  export type TicketCreateManySessionInputEnvelope = {
    data: TicketCreateManySessionInput | TicketCreateManySessionInput[]
    skipDuplicates?: boolean
  }

  export type EventUpsertWithoutSessionsInput = {
    update: XOR<EventUpdateWithoutSessionsInput, EventUncheckedUpdateWithoutSessionsInput>
    create: XOR<EventCreateWithoutSessionsInput, EventUncheckedCreateWithoutSessionsInput>
    where?: EventWhereInput
  }

  export type EventUpdateToOneWithWhereWithoutSessionsInput = {
    where?: EventWhereInput
    data: XOR<EventUpdateWithoutSessionsInput, EventUncheckedUpdateWithoutSessionsInput>
  }

  export type EventUpdateWithoutSessionsInput = {
    id?: StringFieldUpdateOperationsInput | string
    name?: StringFieldUpdateOperationsInput | string
    startDate?: DateTimeFieldUpdateOperationsInput | Date | string
    endDate?: DateTimeFieldUpdateOperationsInput | Date | string
  }

  export type EventUncheckedUpdateWithoutSessionsInput = {
    id?: StringFieldUpdateOperationsInput | string
    name?: StringFieldUpdateOperationsInput | string
    startDate?: DateTimeFieldUpdateOperationsInput | Date | string
    endDate?: DateTimeFieldUpdateOperationsInput | Date | string
  }

  export type CheckInRecordUpsertWithWhereUniqueWithoutSessionInput = {
    where: CheckInRecordWhereUniqueInput
    update: XOR<CheckInRecordUpdateWithoutSessionInput, CheckInRecordUncheckedUpdateWithoutSessionInput>
    create: XOR<CheckInRecordCreateWithoutSessionInput, CheckInRecordUncheckedCreateWithoutSessionInput>
  }

  export type CheckInRecordUpdateWithWhereUniqueWithoutSessionInput = {
    where: CheckInRecordWhereUniqueInput
    data: XOR<CheckInRecordUpdateWithoutSessionInput, CheckInRecordUncheckedUpdateWithoutSessionInput>
  }

  export type CheckInRecordUpdateManyWithWhereWithoutSessionInput = {
    where: CheckInRecordScalarWhereInput
    data: XOR<CheckInRecordUpdateManyMutationInput, CheckInRecordUncheckedUpdateManyWithoutSessionInput>
  }

  export type TicketUpsertWithWhereUniqueWithoutSessionInput = {
    where: TicketWhereUniqueInput
    update: XOR<TicketUpdateWithoutSessionInput, TicketUncheckedUpdateWithoutSessionInput>
    create: XOR<TicketCreateWithoutSessionInput, TicketUncheckedCreateWithoutSessionInput>
  }

  export type TicketUpdateWithWhereUniqueWithoutSessionInput = {
    where: TicketWhereUniqueInput
    data: XOR<TicketUpdateWithoutSessionInput, TicketUncheckedUpdateWithoutSessionInput>
  }

  export type TicketUpdateManyWithWhereWithoutSessionInput = {
    where: TicketScalarWhereInput
    data: XOR<TicketUpdateManyMutationInput, TicketUncheckedUpdateManyWithoutSessionInput>
  }

  export type ChildCreateWithoutTicketsInput = {
    id?: string
    firstName: string
    lastName: string
    birthdate: Date | string
    allergies?: string | null
    notes?: string | null
    qrToken?: string | null
    lastParticipationDate?: Date | string | null
    family: FamilyCreateNestedOneWithoutChildrenInput
    checkInRecords?: CheckInRecordCreateNestedManyWithoutChildInput
  }

  export type ChildUncheckedCreateWithoutTicketsInput = {
    id?: string
    firstName: string
    lastName: string
    birthdate: Date | string
    allergies?: string | null
    notes?: string | null
    qrToken?: string | null
    lastParticipationDate?: Date | string | null
    familyId: string
    checkInRecords?: CheckInRecordUncheckedCreateNestedManyWithoutChildInput
  }

  export type ChildCreateOrConnectWithoutTicketsInput = {
    where: ChildWhereUniqueInput
    create: XOR<ChildCreateWithoutTicketsInput, ChildUncheckedCreateWithoutTicketsInput>
  }

  export type SessionCreateWithoutTicketsInput = {
    id?: string
    name: string
    startTime: Date | string
    endTime: Date | string
    isActive?: boolean
    requiresTicket?: boolean
    event: EventCreateNestedOneWithoutSessionsInput
    checkInRecords?: CheckInRecordCreateNestedManyWithoutSessionInput
  }

  export type SessionUncheckedCreateWithoutTicketsInput = {
    id?: string
    name: string
    startTime: Date | string
    endTime: Date | string
    isActive?: boolean
    requiresTicket?: boolean
    eventId: string
    checkInRecords?: CheckInRecordUncheckedCreateNestedManyWithoutSessionInput
  }

  export type SessionCreateOrConnectWithoutTicketsInput = {
    where: SessionWhereUniqueInput
    create: XOR<SessionCreateWithoutTicketsInput, SessionUncheckedCreateWithoutTicketsInput>
  }

  export type ChildUpsertWithoutTicketsInput = {
    update: XOR<ChildUpdateWithoutTicketsInput, ChildUncheckedUpdateWithoutTicketsInput>
    create: XOR<ChildCreateWithoutTicketsInput, ChildUncheckedCreateWithoutTicketsInput>
    where?: ChildWhereInput
  }

  export type ChildUpdateToOneWithWhereWithoutTicketsInput = {
    where?: ChildWhereInput
    data: XOR<ChildUpdateWithoutTicketsInput, ChildUncheckedUpdateWithoutTicketsInput>
  }

  export type ChildUpdateWithoutTicketsInput = {
    id?: StringFieldUpdateOperationsInput | string
    firstName?: StringFieldUpdateOperationsInput | string
    lastName?: StringFieldUpdateOperationsInput | string
    birthdate?: DateTimeFieldUpdateOperationsInput | Date | string
    allergies?: NullableStringFieldUpdateOperationsInput | string | null
    notes?: NullableStringFieldUpdateOperationsInput | string | null
    qrToken?: NullableStringFieldUpdateOperationsInput | string | null
    lastParticipationDate?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    family?: FamilyUpdateOneRequiredWithoutChildrenNestedInput
    checkInRecords?: CheckInRecordUpdateManyWithoutChildNestedInput
  }

  export type ChildUncheckedUpdateWithoutTicketsInput = {
    id?: StringFieldUpdateOperationsInput | string
    firstName?: StringFieldUpdateOperationsInput | string
    lastName?: StringFieldUpdateOperationsInput | string
    birthdate?: DateTimeFieldUpdateOperationsInput | Date | string
    allergies?: NullableStringFieldUpdateOperationsInput | string | null
    notes?: NullableStringFieldUpdateOperationsInput | string | null
    qrToken?: NullableStringFieldUpdateOperationsInput | string | null
    lastParticipationDate?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    familyId?: StringFieldUpdateOperationsInput | string
    checkInRecords?: CheckInRecordUncheckedUpdateManyWithoutChildNestedInput
  }

  export type SessionUpsertWithoutTicketsInput = {
    update: XOR<SessionUpdateWithoutTicketsInput, SessionUncheckedUpdateWithoutTicketsInput>
    create: XOR<SessionCreateWithoutTicketsInput, SessionUncheckedCreateWithoutTicketsInput>
    where?: SessionWhereInput
  }

  export type SessionUpdateToOneWithWhereWithoutTicketsInput = {
    where?: SessionWhereInput
    data: XOR<SessionUpdateWithoutTicketsInput, SessionUncheckedUpdateWithoutTicketsInput>
  }

  export type SessionUpdateWithoutTicketsInput = {
    id?: StringFieldUpdateOperationsInput | string
    name?: StringFieldUpdateOperationsInput | string
    startTime?: DateTimeFieldUpdateOperationsInput | Date | string
    endTime?: DateTimeFieldUpdateOperationsInput | Date | string
    isActive?: BoolFieldUpdateOperationsInput | boolean
    requiresTicket?: BoolFieldUpdateOperationsInput | boolean
    event?: EventUpdateOneRequiredWithoutSessionsNestedInput
    checkInRecords?: CheckInRecordUpdateManyWithoutSessionNestedInput
  }

  export type SessionUncheckedUpdateWithoutTicketsInput = {
    id?: StringFieldUpdateOperationsInput | string
    name?: StringFieldUpdateOperationsInput | string
    startTime?: DateTimeFieldUpdateOperationsInput | Date | string
    endTime?: DateTimeFieldUpdateOperationsInput | Date | string
    isActive?: BoolFieldUpdateOperationsInput | boolean
    requiresTicket?: BoolFieldUpdateOperationsInput | boolean
    eventId?: StringFieldUpdateOperationsInput | string
    checkInRecords?: CheckInRecordUncheckedUpdateManyWithoutSessionNestedInput
  }

  export type ChildCreateWithoutCheckInRecordsInput = {
    id?: string
    firstName: string
    lastName: string
    birthdate: Date | string
    allergies?: string | null
    notes?: string | null
    qrToken?: string | null
    lastParticipationDate?: Date | string | null
    family: FamilyCreateNestedOneWithoutChildrenInput
    tickets?: TicketCreateNestedManyWithoutChildInput
  }

  export type ChildUncheckedCreateWithoutCheckInRecordsInput = {
    id?: string
    firstName: string
    lastName: string
    birthdate: Date | string
    allergies?: string | null
    notes?: string | null
    qrToken?: string | null
    lastParticipationDate?: Date | string | null
    familyId: string
    tickets?: TicketUncheckedCreateNestedManyWithoutChildInput
  }

  export type ChildCreateOrConnectWithoutCheckInRecordsInput = {
    where: ChildWhereUniqueInput
    create: XOR<ChildCreateWithoutCheckInRecordsInput, ChildUncheckedCreateWithoutCheckInRecordsInput>
  }

  export type SessionCreateWithoutCheckInRecordsInput = {
    id?: string
    name: string
    startTime: Date | string
    endTime: Date | string
    isActive?: boolean
    requiresTicket?: boolean
    event: EventCreateNestedOneWithoutSessionsInput
    tickets?: TicketCreateNestedManyWithoutSessionInput
  }

  export type SessionUncheckedCreateWithoutCheckInRecordsInput = {
    id?: string
    name: string
    startTime: Date | string
    endTime: Date | string
    isActive?: boolean
    requiresTicket?: boolean
    eventId: string
    tickets?: TicketUncheckedCreateNestedManyWithoutSessionInput
  }

  export type SessionCreateOrConnectWithoutCheckInRecordsInput = {
    where: SessionWhereUniqueInput
    create: XOR<SessionCreateWithoutCheckInRecordsInput, SessionUncheckedCreateWithoutCheckInRecordsInput>
  }

  export type AdminUserCreateWithoutCheckInsPerformedInput = {
    id?: string
    username: string
    passwordHash: string
    name: string
    createdAt?: Date | string
    lastLogin?: Date | string | null
    isActive?: boolean
    checkOutsPerformed?: CheckInRecordCreateNestedManyWithoutCheckOutStaffInput
  }

  export type AdminUserUncheckedCreateWithoutCheckInsPerformedInput = {
    id?: string
    username: string
    passwordHash: string
    name: string
    createdAt?: Date | string
    lastLogin?: Date | string | null
    isActive?: boolean
    checkOutsPerformed?: CheckInRecordUncheckedCreateNestedManyWithoutCheckOutStaffInput
  }

  export type AdminUserCreateOrConnectWithoutCheckInsPerformedInput = {
    where: AdminUserWhereUniqueInput
    create: XOR<AdminUserCreateWithoutCheckInsPerformedInput, AdminUserUncheckedCreateWithoutCheckInsPerformedInput>
  }

  export type AdminUserCreateWithoutCheckOutsPerformedInput = {
    id?: string
    username: string
    passwordHash: string
    name: string
    createdAt?: Date | string
    lastLogin?: Date | string | null
    isActive?: boolean
    checkInsPerformed?: CheckInRecordCreateNestedManyWithoutCheckInStaffInput
  }

  export type AdminUserUncheckedCreateWithoutCheckOutsPerformedInput = {
    id?: string
    username: string
    passwordHash: string
    name: string
    createdAt?: Date | string
    lastLogin?: Date | string | null
    isActive?: boolean
    checkInsPerformed?: CheckInRecordUncheckedCreateNestedManyWithoutCheckInStaffInput
  }

  export type AdminUserCreateOrConnectWithoutCheckOutsPerformedInput = {
    where: AdminUserWhereUniqueInput
    create: XOR<AdminUserCreateWithoutCheckOutsPerformedInput, AdminUserUncheckedCreateWithoutCheckOutsPerformedInput>
  }

  export type ChildUpsertWithoutCheckInRecordsInput = {
    update: XOR<ChildUpdateWithoutCheckInRecordsInput, ChildUncheckedUpdateWithoutCheckInRecordsInput>
    create: XOR<ChildCreateWithoutCheckInRecordsInput, ChildUncheckedCreateWithoutCheckInRecordsInput>
    where?: ChildWhereInput
  }

  export type ChildUpdateToOneWithWhereWithoutCheckInRecordsInput = {
    where?: ChildWhereInput
    data: XOR<ChildUpdateWithoutCheckInRecordsInput, ChildUncheckedUpdateWithoutCheckInRecordsInput>
  }

  export type ChildUpdateWithoutCheckInRecordsInput = {
    id?: StringFieldUpdateOperationsInput | string
    firstName?: StringFieldUpdateOperationsInput | string
    lastName?: StringFieldUpdateOperationsInput | string
    birthdate?: DateTimeFieldUpdateOperationsInput | Date | string
    allergies?: NullableStringFieldUpdateOperationsInput | string | null
    notes?: NullableStringFieldUpdateOperationsInput | string | null
    qrToken?: NullableStringFieldUpdateOperationsInput | string | null
    lastParticipationDate?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    family?: FamilyUpdateOneRequiredWithoutChildrenNestedInput
    tickets?: TicketUpdateManyWithoutChildNestedInput
  }

  export type ChildUncheckedUpdateWithoutCheckInRecordsInput = {
    id?: StringFieldUpdateOperationsInput | string
    firstName?: StringFieldUpdateOperationsInput | string
    lastName?: StringFieldUpdateOperationsInput | string
    birthdate?: DateTimeFieldUpdateOperationsInput | Date | string
    allergies?: NullableStringFieldUpdateOperationsInput | string | null
    notes?: NullableStringFieldUpdateOperationsInput | string | null
    qrToken?: NullableStringFieldUpdateOperationsInput | string | null
    lastParticipationDate?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    familyId?: StringFieldUpdateOperationsInput | string
    tickets?: TicketUncheckedUpdateManyWithoutChildNestedInput
  }

  export type SessionUpsertWithoutCheckInRecordsInput = {
    update: XOR<SessionUpdateWithoutCheckInRecordsInput, SessionUncheckedUpdateWithoutCheckInRecordsInput>
    create: XOR<SessionCreateWithoutCheckInRecordsInput, SessionUncheckedCreateWithoutCheckInRecordsInput>
    where?: SessionWhereInput
  }

  export type SessionUpdateToOneWithWhereWithoutCheckInRecordsInput = {
    where?: SessionWhereInput
    data: XOR<SessionUpdateWithoutCheckInRecordsInput, SessionUncheckedUpdateWithoutCheckInRecordsInput>
  }

  export type SessionUpdateWithoutCheckInRecordsInput = {
    id?: StringFieldUpdateOperationsInput | string
    name?: StringFieldUpdateOperationsInput | string
    startTime?: DateTimeFieldUpdateOperationsInput | Date | string
    endTime?: DateTimeFieldUpdateOperationsInput | Date | string
    isActive?: BoolFieldUpdateOperationsInput | boolean
    requiresTicket?: BoolFieldUpdateOperationsInput | boolean
    event?: EventUpdateOneRequiredWithoutSessionsNestedInput
    tickets?: TicketUpdateManyWithoutSessionNestedInput
  }

  export type SessionUncheckedUpdateWithoutCheckInRecordsInput = {
    id?: StringFieldUpdateOperationsInput | string
    name?: StringFieldUpdateOperationsInput | string
    startTime?: DateTimeFieldUpdateOperationsInput | Date | string
    endTime?: DateTimeFieldUpdateOperationsInput | Date | string
    isActive?: BoolFieldUpdateOperationsInput | boolean
    requiresTicket?: BoolFieldUpdateOperationsInput | boolean
    eventId?: StringFieldUpdateOperationsInput | string
    tickets?: TicketUncheckedUpdateManyWithoutSessionNestedInput
  }

  export type AdminUserUpsertWithoutCheckInsPerformedInput = {
    update: XOR<AdminUserUpdateWithoutCheckInsPerformedInput, AdminUserUncheckedUpdateWithoutCheckInsPerformedInput>
    create: XOR<AdminUserCreateWithoutCheckInsPerformedInput, AdminUserUncheckedCreateWithoutCheckInsPerformedInput>
    where?: AdminUserWhereInput
  }

  export type AdminUserUpdateToOneWithWhereWithoutCheckInsPerformedInput = {
    where?: AdminUserWhereInput
    data: XOR<AdminUserUpdateWithoutCheckInsPerformedInput, AdminUserUncheckedUpdateWithoutCheckInsPerformedInput>
  }

  export type AdminUserUpdateWithoutCheckInsPerformedInput = {
    id?: StringFieldUpdateOperationsInput | string
    username?: StringFieldUpdateOperationsInput | string
    passwordHash?: StringFieldUpdateOperationsInput | string
    name?: StringFieldUpdateOperationsInput | string
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
    lastLogin?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    isActive?: BoolFieldUpdateOperationsInput | boolean
    checkOutsPerformed?: CheckInRecordUpdateManyWithoutCheckOutStaffNestedInput
  }

  export type AdminUserUncheckedUpdateWithoutCheckInsPerformedInput = {
    id?: StringFieldUpdateOperationsInput | string
    username?: StringFieldUpdateOperationsInput | string
    passwordHash?: StringFieldUpdateOperationsInput | string
    name?: StringFieldUpdateOperationsInput | string
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
    lastLogin?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    isActive?: BoolFieldUpdateOperationsInput | boolean
    checkOutsPerformed?: CheckInRecordUncheckedUpdateManyWithoutCheckOutStaffNestedInput
  }

  export type AdminUserUpsertWithoutCheckOutsPerformedInput = {
    update: XOR<AdminUserUpdateWithoutCheckOutsPerformedInput, AdminUserUncheckedUpdateWithoutCheckOutsPerformedInput>
    create: XOR<AdminUserCreateWithoutCheckOutsPerformedInput, AdminUserUncheckedCreateWithoutCheckOutsPerformedInput>
    where?: AdminUserWhereInput
  }

  export type AdminUserUpdateToOneWithWhereWithoutCheckOutsPerformedInput = {
    where?: AdminUserWhereInput
    data: XOR<AdminUserUpdateWithoutCheckOutsPerformedInput, AdminUserUncheckedUpdateWithoutCheckOutsPerformedInput>
  }

  export type AdminUserUpdateWithoutCheckOutsPerformedInput = {
    id?: StringFieldUpdateOperationsInput | string
    username?: StringFieldUpdateOperationsInput | string
    passwordHash?: StringFieldUpdateOperationsInput | string
    name?: StringFieldUpdateOperationsInput | string
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
    lastLogin?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    isActive?: BoolFieldUpdateOperationsInput | boolean
    checkInsPerformed?: CheckInRecordUpdateManyWithoutCheckInStaffNestedInput
  }

  export type AdminUserUncheckedUpdateWithoutCheckOutsPerformedInput = {
    id?: StringFieldUpdateOperationsInput | string
    username?: StringFieldUpdateOperationsInput | string
    passwordHash?: StringFieldUpdateOperationsInput | string
    name?: StringFieldUpdateOperationsInput | string
    createdAt?: DateTimeFieldUpdateOperationsInput | Date | string
    lastLogin?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    isActive?: BoolFieldUpdateOperationsInput | boolean
    checkInsPerformed?: CheckInRecordUncheckedUpdateManyWithoutCheckInStaffNestedInput
  }

  export type CheckInRecordCreateManyCheckInStaffInput = {
    id?: string
    checkInTime?: Date | string
    checkOutTime?: Date | string | null
    pickedUpBy?: string | null
    childId: string
    sessionId: string
    checkOutStaffId?: string | null
  }

  export type CheckInRecordCreateManyCheckOutStaffInput = {
    id?: string
    checkInTime?: Date | string
    checkOutTime?: Date | string | null
    pickedUpBy?: string | null
    childId: string
    sessionId: string
    checkInStaffId: string
  }

  export type CheckInRecordUpdateWithoutCheckInStaffInput = {
    id?: StringFieldUpdateOperationsInput | string
    checkInTime?: DateTimeFieldUpdateOperationsInput | Date | string
    checkOutTime?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    pickedUpBy?: NullableStringFieldUpdateOperationsInput | string | null
    child?: ChildUpdateOneRequiredWithoutCheckInRecordsNestedInput
    session?: SessionUpdateOneRequiredWithoutCheckInRecordsNestedInput
    checkOutStaff?: AdminUserUpdateOneWithoutCheckOutsPerformedNestedInput
  }

  export type CheckInRecordUncheckedUpdateWithoutCheckInStaffInput = {
    id?: StringFieldUpdateOperationsInput | string
    checkInTime?: DateTimeFieldUpdateOperationsInput | Date | string
    checkOutTime?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    pickedUpBy?: NullableStringFieldUpdateOperationsInput | string | null
    childId?: StringFieldUpdateOperationsInput | string
    sessionId?: StringFieldUpdateOperationsInput | string
    checkOutStaffId?: NullableStringFieldUpdateOperationsInput | string | null
  }

  export type CheckInRecordUncheckedUpdateManyWithoutCheckInStaffInput = {
    id?: StringFieldUpdateOperationsInput | string
    checkInTime?: DateTimeFieldUpdateOperationsInput | Date | string
    checkOutTime?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    pickedUpBy?: NullableStringFieldUpdateOperationsInput | string | null
    childId?: StringFieldUpdateOperationsInput | string
    sessionId?: StringFieldUpdateOperationsInput | string
    checkOutStaffId?: NullableStringFieldUpdateOperationsInput | string | null
  }

  export type CheckInRecordUpdateWithoutCheckOutStaffInput = {
    id?: StringFieldUpdateOperationsInput | string
    checkInTime?: DateTimeFieldUpdateOperationsInput | Date | string
    checkOutTime?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    pickedUpBy?: NullableStringFieldUpdateOperationsInput | string | null
    child?: ChildUpdateOneRequiredWithoutCheckInRecordsNestedInput
    session?: SessionUpdateOneRequiredWithoutCheckInRecordsNestedInput
    checkInStaff?: AdminUserUpdateOneRequiredWithoutCheckInsPerformedNestedInput
  }

  export type CheckInRecordUncheckedUpdateWithoutCheckOutStaffInput = {
    id?: StringFieldUpdateOperationsInput | string
    checkInTime?: DateTimeFieldUpdateOperationsInput | Date | string
    checkOutTime?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    pickedUpBy?: NullableStringFieldUpdateOperationsInput | string | null
    childId?: StringFieldUpdateOperationsInput | string
    sessionId?: StringFieldUpdateOperationsInput | string
    checkInStaffId?: StringFieldUpdateOperationsInput | string
  }

  export type CheckInRecordUncheckedUpdateManyWithoutCheckOutStaffInput = {
    id?: StringFieldUpdateOperationsInput | string
    checkInTime?: DateTimeFieldUpdateOperationsInput | Date | string
    checkOutTime?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    pickedUpBy?: NullableStringFieldUpdateOperationsInput | string | null
    childId?: StringFieldUpdateOperationsInput | string
    sessionId?: StringFieldUpdateOperationsInput | string
    checkInStaffId?: StringFieldUpdateOperationsInput | string
  }

  export type ParentCreateManyFamilyInput = {
    id?: string
    name: string
    phone?: string | null
    email?: string | null
    relationshipType: string
    lastParticipationDate?: Date | string | null
  }

  export type ChildCreateManyFamilyInput = {
    id?: string
    firstName: string
    lastName: string
    birthdate: Date | string
    allergies?: string | null
    notes?: string | null
    qrToken?: string | null
    lastParticipationDate?: Date | string | null
  }

  export type ParentUpdateWithoutFamilyInput = {
    id?: StringFieldUpdateOperationsInput | string
    name?: StringFieldUpdateOperationsInput | string
    phone?: NullableStringFieldUpdateOperationsInput | string | null
    email?: NullableStringFieldUpdateOperationsInput | string | null
    relationshipType?: StringFieldUpdateOperationsInput | string
    lastParticipationDate?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
  }

  export type ParentUncheckedUpdateWithoutFamilyInput = {
    id?: StringFieldUpdateOperationsInput | string
    name?: StringFieldUpdateOperationsInput | string
    phone?: NullableStringFieldUpdateOperationsInput | string | null
    email?: NullableStringFieldUpdateOperationsInput | string | null
    relationshipType?: StringFieldUpdateOperationsInput | string
    lastParticipationDate?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
  }

  export type ParentUncheckedUpdateManyWithoutFamilyInput = {
    id?: StringFieldUpdateOperationsInput | string
    name?: StringFieldUpdateOperationsInput | string
    phone?: NullableStringFieldUpdateOperationsInput | string | null
    email?: NullableStringFieldUpdateOperationsInput | string | null
    relationshipType?: StringFieldUpdateOperationsInput | string
    lastParticipationDate?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
  }

  export type ChildUpdateWithoutFamilyInput = {
    id?: StringFieldUpdateOperationsInput | string
    firstName?: StringFieldUpdateOperationsInput | string
    lastName?: StringFieldUpdateOperationsInput | string
    birthdate?: DateTimeFieldUpdateOperationsInput | Date | string
    allergies?: NullableStringFieldUpdateOperationsInput | string | null
    notes?: NullableStringFieldUpdateOperationsInput | string | null
    qrToken?: NullableStringFieldUpdateOperationsInput | string | null
    lastParticipationDate?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    checkInRecords?: CheckInRecordUpdateManyWithoutChildNestedInput
    tickets?: TicketUpdateManyWithoutChildNestedInput
  }

  export type ChildUncheckedUpdateWithoutFamilyInput = {
    id?: StringFieldUpdateOperationsInput | string
    firstName?: StringFieldUpdateOperationsInput | string
    lastName?: StringFieldUpdateOperationsInput | string
    birthdate?: DateTimeFieldUpdateOperationsInput | Date | string
    allergies?: NullableStringFieldUpdateOperationsInput | string | null
    notes?: NullableStringFieldUpdateOperationsInput | string | null
    qrToken?: NullableStringFieldUpdateOperationsInput | string | null
    lastParticipationDate?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    checkInRecords?: CheckInRecordUncheckedUpdateManyWithoutChildNestedInput
    tickets?: TicketUncheckedUpdateManyWithoutChildNestedInput
  }

  export type ChildUncheckedUpdateManyWithoutFamilyInput = {
    id?: StringFieldUpdateOperationsInput | string
    firstName?: StringFieldUpdateOperationsInput | string
    lastName?: StringFieldUpdateOperationsInput | string
    birthdate?: DateTimeFieldUpdateOperationsInput | Date | string
    allergies?: NullableStringFieldUpdateOperationsInput | string | null
    notes?: NullableStringFieldUpdateOperationsInput | string | null
    qrToken?: NullableStringFieldUpdateOperationsInput | string | null
    lastParticipationDate?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
  }

  export type CheckInRecordCreateManyChildInput = {
    id?: string
    checkInTime?: Date | string
    checkOutTime?: Date | string | null
    pickedUpBy?: string | null
    sessionId: string
    checkInStaffId: string
    checkOutStaffId?: string | null
  }

  export type TicketCreateManyChildInput = {
    id?: string
    type: string
    sessionId?: string | null
  }

  export type CheckInRecordUpdateWithoutChildInput = {
    id?: StringFieldUpdateOperationsInput | string
    checkInTime?: DateTimeFieldUpdateOperationsInput | Date | string
    checkOutTime?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    pickedUpBy?: NullableStringFieldUpdateOperationsInput | string | null
    session?: SessionUpdateOneRequiredWithoutCheckInRecordsNestedInput
    checkInStaff?: AdminUserUpdateOneRequiredWithoutCheckInsPerformedNestedInput
    checkOutStaff?: AdminUserUpdateOneWithoutCheckOutsPerformedNestedInput
  }

  export type CheckInRecordUncheckedUpdateWithoutChildInput = {
    id?: StringFieldUpdateOperationsInput | string
    checkInTime?: DateTimeFieldUpdateOperationsInput | Date | string
    checkOutTime?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    pickedUpBy?: NullableStringFieldUpdateOperationsInput | string | null
    sessionId?: StringFieldUpdateOperationsInput | string
    checkInStaffId?: StringFieldUpdateOperationsInput | string
    checkOutStaffId?: NullableStringFieldUpdateOperationsInput | string | null
  }

  export type CheckInRecordUncheckedUpdateManyWithoutChildInput = {
    id?: StringFieldUpdateOperationsInput | string
    checkInTime?: DateTimeFieldUpdateOperationsInput | Date | string
    checkOutTime?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    pickedUpBy?: NullableStringFieldUpdateOperationsInput | string | null
    sessionId?: StringFieldUpdateOperationsInput | string
    checkInStaffId?: StringFieldUpdateOperationsInput | string
    checkOutStaffId?: NullableStringFieldUpdateOperationsInput | string | null
  }

  export type TicketUpdateWithoutChildInput = {
    id?: StringFieldUpdateOperationsInput | string
    type?: StringFieldUpdateOperationsInput | string
    session?: SessionUpdateOneWithoutTicketsNestedInput
  }

  export type TicketUncheckedUpdateWithoutChildInput = {
    id?: StringFieldUpdateOperationsInput | string
    type?: StringFieldUpdateOperationsInput | string
    sessionId?: NullableStringFieldUpdateOperationsInput | string | null
  }

  export type TicketUncheckedUpdateManyWithoutChildInput = {
    id?: StringFieldUpdateOperationsInput | string
    type?: StringFieldUpdateOperationsInput | string
    sessionId?: NullableStringFieldUpdateOperationsInput | string | null
  }

  export type SessionCreateManyEventInput = {
    id?: string
    name: string
    startTime: Date | string
    endTime: Date | string
    isActive?: boolean
    requiresTicket?: boolean
  }

  export type SessionUpdateWithoutEventInput = {
    id?: StringFieldUpdateOperationsInput | string
    name?: StringFieldUpdateOperationsInput | string
    startTime?: DateTimeFieldUpdateOperationsInput | Date | string
    endTime?: DateTimeFieldUpdateOperationsInput | Date | string
    isActive?: BoolFieldUpdateOperationsInput | boolean
    requiresTicket?: BoolFieldUpdateOperationsInput | boolean
    checkInRecords?: CheckInRecordUpdateManyWithoutSessionNestedInput
    tickets?: TicketUpdateManyWithoutSessionNestedInput
  }

  export type SessionUncheckedUpdateWithoutEventInput = {
    id?: StringFieldUpdateOperationsInput | string
    name?: StringFieldUpdateOperationsInput | string
    startTime?: DateTimeFieldUpdateOperationsInput | Date | string
    endTime?: DateTimeFieldUpdateOperationsInput | Date | string
    isActive?: BoolFieldUpdateOperationsInput | boolean
    requiresTicket?: BoolFieldUpdateOperationsInput | boolean
    checkInRecords?: CheckInRecordUncheckedUpdateManyWithoutSessionNestedInput
    tickets?: TicketUncheckedUpdateManyWithoutSessionNestedInput
  }

  export type SessionUncheckedUpdateManyWithoutEventInput = {
    id?: StringFieldUpdateOperationsInput | string
    name?: StringFieldUpdateOperationsInput | string
    startTime?: DateTimeFieldUpdateOperationsInput | Date | string
    endTime?: DateTimeFieldUpdateOperationsInput | Date | string
    isActive?: BoolFieldUpdateOperationsInput | boolean
    requiresTicket?: BoolFieldUpdateOperationsInput | boolean
  }

  export type CheckInRecordCreateManySessionInput = {
    id?: string
    checkInTime?: Date | string
    checkOutTime?: Date | string | null
    pickedUpBy?: string | null
    childId: string
    checkInStaffId: string
    checkOutStaffId?: string | null
  }

  export type TicketCreateManySessionInput = {
    id?: string
    type: string
    childId: string
  }

  export type CheckInRecordUpdateWithoutSessionInput = {
    id?: StringFieldUpdateOperationsInput | string
    checkInTime?: DateTimeFieldUpdateOperationsInput | Date | string
    checkOutTime?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    pickedUpBy?: NullableStringFieldUpdateOperationsInput | string | null
    child?: ChildUpdateOneRequiredWithoutCheckInRecordsNestedInput
    checkInStaff?: AdminUserUpdateOneRequiredWithoutCheckInsPerformedNestedInput
    checkOutStaff?: AdminUserUpdateOneWithoutCheckOutsPerformedNestedInput
  }

  export type CheckInRecordUncheckedUpdateWithoutSessionInput = {
    id?: StringFieldUpdateOperationsInput | string
    checkInTime?: DateTimeFieldUpdateOperationsInput | Date | string
    checkOutTime?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    pickedUpBy?: NullableStringFieldUpdateOperationsInput | string | null
    childId?: StringFieldUpdateOperationsInput | string
    checkInStaffId?: StringFieldUpdateOperationsInput | string
    checkOutStaffId?: NullableStringFieldUpdateOperationsInput | string | null
  }

  export type CheckInRecordUncheckedUpdateManyWithoutSessionInput = {
    id?: StringFieldUpdateOperationsInput | string
    checkInTime?: DateTimeFieldUpdateOperationsInput | Date | string
    checkOutTime?: NullableDateTimeFieldUpdateOperationsInput | Date | string | null
    pickedUpBy?: NullableStringFieldUpdateOperationsInput | string | null
    childId?: StringFieldUpdateOperationsInput | string
    checkInStaffId?: StringFieldUpdateOperationsInput | string
    checkOutStaffId?: NullableStringFieldUpdateOperationsInput | string | null
  }

  export type TicketUpdateWithoutSessionInput = {
    id?: StringFieldUpdateOperationsInput | string
    type?: StringFieldUpdateOperationsInput | string
    child?: ChildUpdateOneRequiredWithoutTicketsNestedInput
  }

  export type TicketUncheckedUpdateWithoutSessionInput = {
    id?: StringFieldUpdateOperationsInput | string
    type?: StringFieldUpdateOperationsInput | string
    childId?: StringFieldUpdateOperationsInput | string
  }

  export type TicketUncheckedUpdateManyWithoutSessionInput = {
    id?: StringFieldUpdateOperationsInput | string
    type?: StringFieldUpdateOperationsInput | string
    childId?: StringFieldUpdateOperationsInput | string
  }



  /**
   * Batch Payload for updateMany & deleteMany & createMany
   */

  export type BatchPayload = {
    count: number
  }

  /**
   * DMMF
   */
  export const dmmf: runtime.BaseDMMF
}